import { useMutation, useQuery } from "@tanstack/react-query";
import { createFileRoute, redirect } from "@tanstack/react-router";
import {
  addEdge,
  Background,
  type Connection,
  Controls,
  type Edge,
  MiniMap,
  type Node,
  ReactFlow,
  type ReactFlowInstance,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "@xyflow/react/dist/style.css";
import { css } from "../../styled-system/css";
import { CustomNode, type CustomNodeData } from "../components/workflow/CustomNode";
import { EditorToolbar } from "../components/workflow/EditorToolbar";
import { NodeInspector } from "../components/workflow/NodeInspector";
import { NodePalette, type NodeTypeDefinition } from "../components/workflow/NodePalette";
import { api } from "../lib/api";

export const Route = createFileRoute("/workflows_/$workflowId/edit")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: WorkflowEditorPage,
});

interface WorkflowData {
  id: number;
  name: string;
  number: string;
  description: string;
  workflow_type: string;
  extension_id: number | null;
  enabled: boolean;
  definition: {
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
  };
}

interface WorkflowNode {
  id: string;
  type: string;
  label: string;
  position: { x: number; y: number };
  config: Record<string, unknown>;
}

interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
  label?: string;
}

const nodeTypes = { custom: CustomNode };

function WorkflowEditorPage() {
  const { workflowId } = Route.useParams();
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Undo/Redo history
  const historyRef = useRef<{ nodes: Node[]; edges: Edge[] }[]>([]);
  const historyIndexRef = useRef(-1);
  const skipHistoryRef = useRef(false);

  const pushHistory = useCallback(() => {
    if (skipHistoryRef.current) return;
    const snapshot = { nodes: structuredClone(nodes), edges: structuredClone(edges) };
    const idx = historyIndexRef.current;
    historyRef.current = historyRef.current.slice(0, idx + 1);
    historyRef.current.push(snapshot);
    if (historyRef.current.length > 50) historyRef.current.shift();
    historyIndexRef.current = historyRef.current.length - 1;
  }, [nodes, edges]);

  // Save snapshot after changes settle (debounced)
  const pushTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => {
    clearTimeout(pushTimerRef.current);
    pushTimerRef.current = setTimeout(pushHistory, 300);
    return () => clearTimeout(pushTimerRef.current);
  }, [pushHistory]);

  const undo = useCallback(() => {
    const idx = historyIndexRef.current;
    if (idx <= 0) return;
    historyIndexRef.current = idx - 1;
    const prev = historyRef.current[idx - 1];
    skipHistoryRef.current = true;
    setNodes(structuredClone(prev.nodes));
    setEdges(structuredClone(prev.edges));
    requestAnimationFrame(() => {
      skipHistoryRef.current = false;
    });
  }, [setNodes, setEdges]);

  const redo = useCallback(() => {
    const idx = historyIndexRef.current;
    if (idx >= historyRef.current.length - 1) return;
    historyIndexRef.current = idx + 1;
    const next = historyRef.current[idx + 1];
    skipHistoryRef.current = true;
    setNodes(structuredClone(next.nodes));
    setEdges(structuredClone(next.edges));
    requestAnimationFrame(() => {
      skipHistoryRef.current = false;
    });
  }, [setNodes, setEdges]);

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "z") {
        e.preventDefault();
        if (e.shiftKey) {
          redo();
        } else {
          undo();
        }
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "y") {
        e.preventDefault();
        redo();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [undo, redo]);

  const { data: workflow, isLoading: wfLoading } = useQuery({
    queryKey: ["workflow", workflowId],
    queryFn: () => api.get<WorkflowData>(`/workflows/${workflowId}`),
  });

  const { data: rawNodeTypes } = useQuery({
    queryKey: ["node-types", workflow?.workflow_type],
    queryFn: () =>
      api.get<Record<string, Omit<NodeTypeDefinition, "type">>>(
        `/workflows/node-types?workflow_type=${workflow?.workflow_type}`,
      ),
    enabled: !!workflow?.workflow_type,
  });

  const nodeTypeDefs = useMemo(() => {
    if (!rawNodeTypes) return [];
    return Object.entries(rawNodeTypes).map(([key, val]) => ({
      type: key,
      ...val,
      config_schema: val.config_schema
        ? Object.entries(
            val.config_schema as unknown as Record<string, Record<string, unknown>>,
          ).map(([fieldName, fieldDef]) => {
            // Normalize options: API returns string[] but frontend expects {value, label}[]
            let options: { value: string; label: string }[] | undefined;
            if (Array.isArray(fieldDef.options)) {
              options = (fieldDef.options as unknown[]).map((opt) =>
                typeof opt === "string"
                  ? { value: opt, label: opt }
                  : (opt as { value: string; label: string }),
              );
            }
            return {
              name: fieldName,
              label: (fieldDef.label as string) || fieldName,
              type: (fieldDef.type as string) || "string",
              required: fieldDef.required as boolean | undefined,
              default: fieldDef.default,
              options,
            };
          })
        : [],
    })) as NodeTypeDefinition[];
  }, [rawNodeTypes]);

  const nodeTypeMap = useMemo(() => {
    const map = new Map<string, NodeTypeDefinition>();
    for (const nt of nodeTypeDefs) {
      map.set(nt.type, nt);
    }
    return map;
  }, [nodeTypeDefs]);

  // Initialize nodes/edges from workflow data once loaded
  const initializedRef = useRef(false);
  if (workflow && nodeTypeDefs.length > 0 && !initializedRef.current) {
    initializedRef.current = true;
    const def = workflow.definition || { nodes: [], edges: [] };

    const rfNodes: Node[] = (def.nodes || []).map((n) => {
      const nt = nodeTypeMap.get(n.type);
      return {
        id: n.id,
        type: "custom",
        position: n.position,
        data: {
          label: nt?.label || n.label || n.type,
          nodeType: n.type,
          color: nt?.color || "#4a4a52",
          config: n.config || {},
        } satisfies CustomNodeData,
      };
    });

    const rfEdges: Edge[] = (def.edges || []).map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.sourceHandle || undefined,
      targetHandle: e.targetHandle || undefined,
      label: e.label || e.sourceHandle || undefined,
      animated: true,
      style: { stroke: "#d4d2cd", strokeWidth: 2 },
    }));

    setNodes(rfNodes);
    setEdges(rfEdges);
  }

  const saveMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.put(`/workflows/${workflowId}`, body),
  });

  // AI Generation
  const [showAiModal, setShowAiModal] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");
  const aiMutation = useMutation({
    mutationFn: (prompt: string) =>
      api.post<{ definition?: { nodes: WorkflowNode[]; edges: WorkflowEdge[] }; error?: string }>(
        "/workflows/generate",
        { prompt, workflow_type: workflow?.workflow_type ?? "ivr" },
      ),
    onSuccess: (result) => {
      if (result.error) {
        alert(`生成エラー: ${result.error}`);
        return;
      }
      if (result.definition) {
        const def = result.definition;
        const rfNodes: Node[] = (def.nodes || []).map((n) => {
          const nt = nodeTypeMap.get(n.type);
          return {
            id: n.id,
            type: "custom",
            position: n.position,
            data: {
              label: nt?.label || n.label || n.type,
              nodeType: n.type,
              color: nt?.color || "#4a4a52",
              config: n.config || {},
            } satisfies CustomNodeData,
          };
        });
        const rfEdges: Edge[] = (def.edges || []).map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          sourceHandle: e.sourceHandle || undefined,
          targetHandle: e.targetHandle || undefined,
          label: e.label || e.sourceHandle || undefined,
          animated: true,
          style: { stroke: "#d4d2cd", strokeWidth: 2 },
        }));
        setNodes(rfNodes);
        setEdges(rfEdges);
        setShowAiModal(false);
        setAiPrompt("");
      }
    },
  });

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge(connection, eds));
    },
    [setEdges],
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const raw = e.dataTransfer.getData("application/millicall-node");
      if (!raw) return;

      const nodeType: NodeTypeDefinition = JSON.parse(raw);
      if (!rfInstance || !reactFlowWrapper.current) return;

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = rfInstance.screenToFlowPosition({
        x: e.clientX - bounds.left,
        y: e.clientY - bounds.top,
      });

      const newId = `node_${Date.now()}`;
      const defaults: Record<string, unknown> = {};
      for (const f of nodeType.config_schema) {
        if (f.default !== undefined) defaults[f.name] = f.default;
      }

      const newNode: Node = {
        id: newId,
        type: "custom",
        position,
        data: {
          label: nodeType.label,
          nodeType: nodeType.type,
          color: nodeType.color,
          config: defaults,
        } satisfies CustomNodeData,
      };

      setNodes((nds) => [...nds, newNode]);
    },
    [rfInstance, setNodes],
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  function handleConfigChange(nodeId: string, config: Record<string, unknown>) {
    setNodes((nds) =>
      nds.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, config } } : n)),
    );
  }

  function handleSave() {
    const defNodes: WorkflowNode[] = nodes.map((n) => {
      const d = n.data as unknown as CustomNodeData;
      return {
        id: n.id,
        type: d.nodeType,
        label: d.label,
        position: n.position,
        config: d.config || {},
      };
    });
    const defEdges: WorkflowEdge[] = edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.sourceHandle || undefined,
      targetHandle: e.targetHandle || undefined,
      label: e.sourceHandle || (typeof e.label === "string" ? e.label : undefined),
    }));

    saveMutation.mutate({
      name: workflow?.name ?? "",
      description: workflow?.description ?? "",
      workflow_type: workflow?.workflow_type ?? "ivr",
      number: workflow?.number ?? "",
      extension_id: workflow?.extension_id ?? null,
      enabled: workflow?.enabled ?? true,
      definition: { nodes: defNodes, edges: defEdges },
    });
  }

  if (wfLoading) {
    return (
      <div className={css({ padding: "48px", textAlign: "center", color: "#4a4a52" })}>
        読み込み中...
      </div>
    );
  }

  if (!workflow) {
    return (
      <div className={css({ padding: "48px", textAlign: "center", color: "#b83232" })}>
        ワークフローが見つかりません
      </div>
    );
  }

  const selectedNode = selectedNodeId ? nodes.find((n) => n.id === selectedNodeId) : null;
  const selectedNodeType = selectedNode
    ? nodeTypeMap.get((selectedNode.data as unknown as CustomNodeData).nodeType)
    : undefined;

  return (
    <div
      className={css({
        position: "fixed",
        top: "48px",
        left: "0",
        right: "0",
        bottom: "0",
        display: "flex",
        flexDirection: "column",
        background: "#f0eeeb",
        zIndex: 50,
      })}
    >
      <EditorToolbar
        workflowName={workflow.name}
        onSave={handleSave}
        isSaving={saveMutation.isPending}
        onAiGenerate={() => setShowAiModal(true)}
        isGenerating={aiMutation.isPending}
      />

      <div className={css({ display: "flex", flex: 1, overflow: "hidden" })}>
        <NodePalette nodeTypes={nodeTypeDefs} />

        <div ref={reactFlowWrapper} className={css({ flex: 1, position: "relative" })}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setRfInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={16} size={1} color="#d4d2cd" />
            <Controls showInteractive={false} position="bottom-left" />
            <MiniMap
              nodeColor={(n) => {
                const d = n.data as unknown as CustomNodeData;
                return d.color || "#4a4a52";
              }}
              maskColor="rgba(240,238,235,0.7)"
              position="bottom-right"
            />
          </ReactFlow>
        </div>

        {selectedNode && (
          <NodeInspector
            nodeId={selectedNode.id}
            nodeType={selectedNodeType}
            config={
              ((selectedNode.data as unknown as CustomNodeData).config as Record<
                string,
                unknown
              >) || {}
            }
            onConfigChange={handleConfigChange}
            onClose={() => setSelectedNodeId(null)}
          />
        )}
      </div>

      {/* AI Generation Modal */}
      {showAiModal && (
        // biome-ignore lint/a11y/noStaticElementInteractions: modal backdrop overlay
        <div
          role="presentation"
          className={css({
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 200,
          })}
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowAiModal(false);
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") setShowAiModal(false);
          }}
        >
          <div
            className={css({
              background: "#ffffff",
              borderRadius: "8px",
              boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
              width: "90%",
              maxWidth: "560px",
              padding: "24px",
            })}
          >
            <div
              className={css({
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "16px",
              })}
            >
              <h2 className={css({ fontSize: "16px", fontWeight: 700, color: "#1b1b1f" })}>
                ✦ AIでワークフローを生成
              </h2>
              <button
                type="button"
                onClick={() => setShowAiModal(false)}
                className={css({
                  background: "transparent",
                  border: "none",
                  fontSize: "20px",
                  cursor: "pointer",
                  color: "#8e8e96",
                  _hover: { color: "#1b1b1f" },
                })}
              >
                &times;
              </button>
            </div>
            <p className={css({ fontSize: "13px", color: "#4a4a52", marginBottom: "12px" })}>
              どんなワークフローを作りたいか自然言語で記述してください。AIがノードとエッジを自動生成します。
            </p>
            <textarea
              className={css({
                width: "100%",
                minHeight: "120px",
                padding: "10px",
                fontSize: "14px",
                border: "1px solid #d4d2cd",
                borderRadius: "5px",
                outline: "none",
                resize: "vertical",
                fontFamily: "'Noto Sans JP', sans-serif",
                _focus: { borderColor: "#673AB7" },
              })}
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              placeholder="例: 営業時間内（平日9-18時）はAIが受付応対し、名前と用件を聞いてから内線4001に転送。時間外は留守番電話にする。"
            />
            <div
              className={css({
                display: "flex",
                justifyContent: "flex-end",
                gap: "8px",
                marginTop: "16px",
              })}
            >
              <button
                type="button"
                onClick={() => setShowAiModal(false)}
                className={css({
                  padding: "8px 16px",
                  fontSize: "13px",
                  fontWeight: 500,
                  borderRadius: "5px",
                  background: "#ffffff",
                  color: "#1b1b1f",
                  border: "1px solid #d4d2cd",
                  cursor: "pointer",
                  _hover: { background: "#e6e4e0" },
                })}
              >
                キャンセル
              </button>
              <button
                type="button"
                onClick={() => {
                  if (aiPrompt.trim()) aiMutation.mutate(aiPrompt.trim());
                }}
                disabled={aiMutation.isPending || !aiPrompt.trim()}
                className={css({
                  padding: "8px 16px",
                  fontSize: "13px",
                  fontWeight: 500,
                  borderRadius: "5px",
                  background: "#673AB7",
                  color: "#ffffff",
                  border: "none",
                  cursor: "pointer",
                  _hover: { background: "#5e35b1" },
                  _disabled: { opacity: 0.5 },
                })}
              >
                {aiMutation.isPending ? "生成中..." : "生成する"}
              </button>
            </div>
            {aiMutation.isPending && (
              <p
                className={css({
                  fontSize: "12px",
                  color: "#8e8e96",
                  marginTop: "8px",
                  textAlign: "center",
                })}
              >
                Gemini 2.5 Flashでワークフローを生成しています...
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
