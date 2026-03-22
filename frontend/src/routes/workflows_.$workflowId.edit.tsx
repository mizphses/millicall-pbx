import { useMutation, useQuery } from "@tanstack/react-query";
import { createFileRoute, redirect } from "@tanstack/react-router";
import { useCallback, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
  type Node,
  type Edge,
  type ReactFlowInstance,
} from "@xyflow/react";
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
        ? Object.entries(val.config_schema as unknown as Record<string, Record<string, unknown>>).map(
            ([fieldName, fieldDef]) => {
              // Normalize options: API returns string[] but frontend expects {value, label}[]
              let options: { value: string; label: string }[] | undefined;
              if (Array.isArray(fieldDef.options)) {
                options = (fieldDef.options as unknown[]).map((opt) =>
                  typeof opt === "string" ? { value: opt, label: opt } : (opt as { value: string; label: string }),
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
            },
          )
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
    mutationFn: (body: Record<string, unknown>) =>
      api.put(`/workflows/${workflowId}`, body),
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
      nds.map((n) =>
        n.id === nodeId
          ? { ...n, data: { ...n.data, config } }
          : n,
      ),
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
      />

      <div className={css({ display: "flex", flex: 1, overflow: "hidden" })}>
        <NodePalette nodeTypes={nodeTypeDefs} />

        <div
          ref={reactFlowWrapper}
          className={css({ flex: 1, position: "relative" })}
        >
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
            <Controls
              showInteractive={false}
              position="bottom-left"
            />
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
              ((selectedNode.data as unknown as CustomNodeData).config as Record<string, unknown>) ||
              {}
            }
            onConfigChange={handleConfigChange}
            onClose={() => setSelectedNodeId(null)}
          />
        )}
      </div>
    </div>
  );
}
