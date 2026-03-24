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
import {
  FormGroup,
  FormRow,
  FormSection,
  inputClass,
  selectClass,
  textareaClass,
} from "../components/FormCard";
import { CustomNode, type CustomNodeData } from "../components/workflow/CustomNode";
import { EditorToolbar } from "../components/workflow/EditorToolbar";
import { NodeInspector } from "../components/workflow/NodeInspector";
import { NodePalette, type NodeTypeDefinition } from "../components/workflow/NodePalette";
import { $api } from "../lib/client";

export const Route = createFileRoute("/workflows_/$workflowId/edit")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: WorkflowEditorPage,
});

// Keep local interfaces for untyped API responses (node-types, generate)
interface WorkflowNode {
  id: string;
  type: string;
  label: string;
  position: { x: number; y: number };
  config: Record<string, unknown>;
  data: Record<string, unknown>;
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

  const { data: workflow, isLoading: wfLoading } = $api.useQuery(
    "get",
    "/api/workflows/{workflow_id}",
    { params: { path: { workflow_id: Number(workflowId) } } },
  );

  const { data: rawNodeTypes } = $api.useQuery("get", "/api/workflows/node-types", {
    params: { query: { workflow_type: workflow?.workflow_type ?? "workflow" } },
    enabled: !!workflow?.workflow_type,
  });

  const nodeTypeDefs = useMemo(() => {
    if (!rawNodeTypes) return [];
    const raw = rawNodeTypes as Record<string, Omit<NodeTypeDefinition, "type">>;
    return Object.entries(raw).map(([key, val]) => ({
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

  const saveMutation = $api.useMutation("put", "/api/workflows/{workflow_id}");

  // Basic info editing
  const [showInfoModal, setShowInfoModal] = useState(false);
  const [editName, setEditName] = useState("");
  const [editNumber, setEditNumber] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editEnabled, setEditEnabled] = useState(true);
  const [editTtsProvider, setEditTtsProvider] = useState("google");
  const [editGoogleVoice, setEditGoogleVoice] = useState("ja-JP-Chirp3-HD-Aoede");
  const [editCoefontId, setEditCoefontId] = useState("");

  function openInfoModal() {
    if (workflow) {
      setEditName(workflow.name);
      setEditNumber(workflow.number);
      setEditDescription(workflow.description);
      setEditEnabled(workflow.enabled);
      const tts = workflow.default_tts_config;
      setEditTtsProvider(tts?.tts_provider || "google");
      setEditGoogleVoice(tts?.google_tts_voice || "ja-JP-Chirp3-HD-Aoede");
      setEditCoefontId(tts?.coefont_voice_id || "");
    }
    setShowInfoModal(true);
  }

  const infoMutation = $api.useMutation("put", "/api/workflows/{workflow_id}", {
    onSuccess: () => {
      setShowInfoModal(false);
      // Refetch workflow data
      window.location.reload();
    },
  });

  function handleInfoSave() {
    infoMutation.mutate({
      params: { path: { workflow_id: Number(workflowId) } },
      body: {
        name: editName,
        number: editNumber,
        description: editDescription,
        enabled: editEnabled,
        default_tts_config: {
          tts_provider: editTtsProvider,
          google_tts_voice: editGoogleVoice,
          coefont_voice_id: editCoefontId,
        },
      },
    });
  }

  // AI Generation
  const [showAiModal, setShowAiModal] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");
  const aiMutation = $api.useMutation("post", "/api/workflows/generate", {
    onSuccess: (rawResult) => {
      const result = rawResult as {
        definition?: { nodes: WorkflowNode[]; edges: WorkflowEdge[] };
        error?: string;
      };
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
      // Apply workflow-level default TTS config
      if (workflow?.default_tts_config) {
        const tts = workflow.default_tts_config;
        const ttsFields = ["tts_provider", "google_tts_voice", "coefont_voice_id"] as const;
        for (const key of ttsFields) {
          if (key in defaults && tts[key]) {
            defaults[key] = tts[key];
          }
        }
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
        data: {},
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
      params: { path: { workflow_id: Number(workflowId) } },
      body: {
        name: workflow?.name ?? "",
        description: workflow?.description ?? "",
        workflow_type: workflow?.workflow_type ?? "workflow",
        number: workflow?.number ?? "",
        enabled: workflow?.enabled ?? true,
        definition: { nodes: defNodes, edges: defEdges },
      },
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
        onEditInfo={openInfoModal}
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
                  if (aiPrompt.trim()) aiMutation.mutate({ body: { prompt: aiPrompt.trim(), workflow_type: "workflow" } });
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

      {/* Basic Info Modal */}
      {showInfoModal && (
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
            if (e.target === e.currentTarget) setShowInfoModal(false);
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") setShowInfoModal(false);
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
              maxHeight: "80vh",
              overflowY: "auto",
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
                ワークフロー設定
              </h2>
              <button
                type="button"
                onClick={() => setShowInfoModal(false)}
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

            <FormSection title="基本情報" />
            <FormRow>
              <FormGroup label="名前">
                <input
                  type="text"
                  className={inputClass}
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  required
                />
              </FormGroup>
              <FormGroup label="内線番号">
                <input
                  type="text"
                  className={inputClass}
                  value={editNumber}
                  onChange={(e) => setEditNumber(e.target.value)}
                  required
                  pattern="\d+"
                />
              </FormGroup>
            </FormRow>
            <FormGroup label="説明">
              <textarea
                className={textareaClass}
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                rows={3}
              />
            </FormGroup>

            <FormSection title="デフォルトTTS設定" />
            <FormRow>
              <FormGroup label="TTSプロバイダ">
                <select
                  className={selectClass}
                  value={editTtsProvider}
                  onChange={(e) => setEditTtsProvider(e.target.value)}
                >
                  <option value="google">Google Chirp3 HD</option>
                  <option value="coefont">CoeFont</option>
                </select>
              </FormGroup>
              {editTtsProvider === "google" ? (
                <FormGroup label="Google TTSボイス">
                  <select
                    className={selectClass}
                    value={editGoogleVoice}
                    onChange={(e) => setEditGoogleVoice(e.target.value)}
                  >
                    <option value="ja-JP-Chirp3-HD-Aoede">Aoede</option>
                    <option value="ja-JP-Chirp3-HD-Kore">Kore</option>
                    <option value="ja-JP-Chirp3-HD-Leda">Leda</option>
                    <option value="ja-JP-Chirp3-HD-Zephyr">Zephyr</option>
                    <option value="ja-JP-Chirp3-HD-Charon">Charon</option>
                    <option value="ja-JP-Chirp3-HD-Fenrir">Fenrir</option>
                    <option value="ja-JP-Chirp3-HD-Orus">Orus</option>
                    <option value="ja-JP-Chirp3-HD-Puck">Puck</option>
                  </select>
                </FormGroup>
              ) : (
                <FormGroup label="CoeFont ボイスID">
                  <input
                    type="text"
                    className={inputClass}
                    value={editCoefontId}
                    onChange={(e) => setEditCoefontId(e.target.value)}
                    placeholder="ボイスID"
                  />
                </FormGroup>
              )}
            </FormRow>

            <label
              className={css({
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "14px",
                cursor: "pointer",
                paddingBlock: "4px",
                marginTop: "12px",
              })}
            >
              <input
                type="checkbox"
                className={css({ width: "16px", height: "16px", accentColor: "#c45d2c" })}
                checked={editEnabled}
                onChange={(e) => setEditEnabled(e.target.checked)}
              />
              このワークフローを有効にする
            </label>

            <div
              className={css({
                display: "flex",
                justifyContent: "flex-end",
                gap: "8px",
                marginTop: "20px",
              })}
            >
              <button
                type="button"
                onClick={() => setShowInfoModal(false)}
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
                onClick={handleInfoSave}
                disabled={infoMutation.isPending}
                className={css({
                  padding: "8px 16px",
                  fontSize: "13px",
                  fontWeight: 500,
                  borderRadius: "5px",
                  background: "#c45d2c",
                  color: "#ffffff",
                  border: "none",
                  cursor: "pointer",
                  _hover: { background: "#a84e24" },
                  _disabled: { opacity: 0.5 },
                })}
              >
                {infoMutation.isPending ? "保存中..." : "保存"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
