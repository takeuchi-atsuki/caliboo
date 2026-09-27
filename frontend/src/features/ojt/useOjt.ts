import { useCallback, useEffect, useState } from "react";

import { apiClient } from "../../lib/apiClient";
import type { ChatMessage, Department, KnowledgeItem } from "../../lib/types";

const QUICK_ASKS = ["よく聞かれる質問は？", "参考資料はどこにある？", "初日にやることは？"];

export function useOjt() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedDeptId, setSelectedDeptId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [knowledge, setKnowledge] = useState<KnowledgeItem[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    apiClient.get<{ departments: Department[] }>("/api/ojt/departments").then((data) => {
      setDepartments(data.departments);
    });
  }, []);

  const selectDept = useCallback(async (deptId: string) => {
    setSelectedDeptId(deptId);
    setInput("");
    const [messagesRes, knowledgeRes] = await Promise.all([
      apiClient.get<{ messages: ChatMessage[] }>(`/api/ojt/departments/${deptId}/messages`),
      apiClient.get<{ items: KnowledgeItem[] }>(`/api/ojt/departments/${deptId}/knowledge`),
    ]);
    setMessages(messagesRes.messages);
    setKnowledge(knowledgeRes.items);
  }, []);

  const backToDeptList = useCallback(() => {
    setSelectedDeptId(null);
    setMessages([]);
    setKnowledge([]);
    setInput("");
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!selectedDeptId || !text.trim()) return;
      const myMessage: ChatMessage = {
        id: `local-${Date.now()}-${Math.random()}`,
        role: "me",
        text,
        references: [],
      };
      setMessages((prev) => [...prev, myMessage]);
      setInput("");
      setSending(true);
      try {
        const reply = await apiClient.post<ChatMessage>("/api/ojt/chat", {
          deptId: selectedDeptId,
          text,
        });
        setMessages((prev) => [...prev, reply]);
      } finally {
        setSending(false);
      }
    },
    [selectedDeptId],
  );

  const selectedDept = departments.find((d) => d.id === selectedDeptId) ?? null;

  return {
    departments,
    selectedDept,
    messages,
    knowledge,
    input,
    setInput,
    sending,
    selectDept,
    backToDeptList,
    sendMessage,
    quickAsks: QUICK_ASKS,
  };
}
