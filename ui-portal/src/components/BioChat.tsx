"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import ChatBubble, { type ChatBubbleMessage } from "@/components/ChatBubble";
import { summarizeTriplets } from "@/lib/discovery";
import { getOrganOption } from "@/lib/organs";
import type { TripletData } from "@/services/bioService";
import { intelligenceService } from "@/services/intelligenceService";

interface Props {
  data?: TripletData;
  organType: string;
}

export default function BioChat({ data, organType }: Props): React.JSX.Element {
  const [input, setInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [messages, setMessages] = useState<ChatBubbleMessage[]>([]);
  const [statusText, setStatusText] = useState<string>("Ready");
  const activeRequestRef = useRef<AbortController | null>(null);

  const organ = getOrganOption(organType);
  const summary = useMemo(() => summarizeTriplets(data), [data]);
  const currentGene = summary.genes[0];
  const currentDisease = summary.diseases[0];
  const currentMedicine = summary.medicines[0];
  const currentUniprotId =
    typeof currentGene?.properties?.uniprot_id === "string"
      ? currentGene.properties.uniprot_id
      : undefined;
  const promptSuggestions = useMemo(() => {
    const activeTarget = currentGene?.label ?? organ.primaryTarget;
    return [
      `What is ${activeTarget}?`,
      `What leads do we have for ${activeTarget}?`,
      currentDisease && currentMedicine
        ? `What should we test next for ${currentDisease} and ${currentMedicine}?`
        : `What is the focus of the ${organ.label} organ atlas?`,
      currentDisease ? `Show historical trends for ${currentDisease.label}` : `Show trends for Lung cancer`,
    ];
  }, [currentDisease, currentGene?.label, currentMedicine, organ.label, organ.primaryTarget]);

  useEffect(() => {
    setMessages([
      {
        id: `assistant-${organType}`,
        role: "assistant",
        text:
          currentGene && currentDisease && currentMedicine
            ? `Active ${organ.label} context: ${currentGene.label} links to ${currentDisease.label} and ${currentMedicine.label}. Ask for drug leads, pathway context, or a GEO study explanation.`
            : `Active ${organ.label} context loaded. Ask about ${organ.primaryTarget}, a UniProt ID, or a GEO study accession.`,
      },
    ]);
    setStatusText("Ready");
  }, [currentDisease, currentGene, currentMedicine, organ.label, organ.primaryTarget, organType]);

  useEffect(() => {
    return () => {
      activeRequestRef.current?.abort();
    };
  }, []);

  const submitPrompt = async (rawPrompt: string) => {
    const prompt = rawPrompt.trim();
    if (!prompt || isSubmitting) {
      return;
    }

    const userMessage: ChatBubbleMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      text: prompt,
    };

    const nextHistory = [...messages.slice(-5), userMessage].map((message) => ({
      role: message.role,
      text: message.text,
    }));

    setMessages((current) => [...current, userMessage]);
    setInput("");
    setIsSubmitting(true);
    setStatusText("Querying");
    activeRequestRef.current?.abort();
    const controller = new AbortController();
    activeRequestRef.current = controller;

    try {
      const reply = await intelligenceService.query({
        prompt,
        organ: organType,
        gene: currentGene?.label,
        uniprot_id: currentUniprotId,
        disease: currentDisease?.label,
        medicine: currentMedicine?.label,
        history: nextHistory,
      }, controller.signal);

      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          text: reply.reply,
          sources: reply.sources,
          visualPayload: reply.visual_payload ?? undefined,
        },
      ]);
      setStatusText("Live");
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }
      setMessages((current) => [
        ...current,
        {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          text:
            error instanceof Error
              ? error.message
              : "The intelligence bridge is unavailable.",
        },
      ]);
      setStatusText("Degraded");
    } finally {
      if (activeRequestRef.current === controller) {
        activeRequestRef.current = null;
      }
      setIsSubmitting(false);
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    await submitPrompt(input);
  };

  return (
    <aside className="w-80 h-full bg-surface-container-low border-l border-outline-variant/15 flex flex-col shrink-0">
      <div className="p-6 border-b border-outline-variant/10">
        <div className="flex items-center justify-between mb-4">
          <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
            Intelligence
          </span>
          <span className="text-[10px] font-mono text-tertiary bg-tertiary/10 px-1.5 rounded">
            {statusText === "Live" ? "ONLINE" : statusText === "Querying" ? "QUERYING" : statusText}
          </span>
        </div>
        <h3 className="text-xl font-headline font-bold text-on-surface mb-1">
          Bio-Chat Assistant
        </h3>
        <p className="text-xs text-on-surface-variant leading-relaxed opacity-80">
          Query the knowledge graph and RAG context via FastMCP.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto no-scrollbar p-6 space-y-4">
        <div className="flex flex-wrap gap-2">
          {promptSuggestions.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              disabled={isSubmitting}
              onClick={() => {
                void submitPrompt(suggestion);
              }}
              className="rounded-full border border-outline-variant/15 bg-surface-container px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant transition-colors hover:border-primary/40 hover:text-primary"
            >
              {suggestion}
            </button>
          ))}
        </div>
        {messages.map((message) => (
          <ChatBubble key={message.id} message={message} />
        ))}
      </div>

      <div className="p-6 bg-surface-container-lowest border-t border-outline-variant/10">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-10 h-10 rounded bg-secondary-container flex items-center justify-center">
            <span className="material-symbols-outlined text-secondary">science</span>
          </div>
          <div>
            <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-tighter">
              Analysis Engine
            </p>
            <p className="text-xs font-semibold text-secondary">
              {statusText === "Querying" ? "Running Query" : `Context: ${organ.label}`}
            </p>
          </div>
        </div>
        <form onSubmit={handleSend} className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Bio-Chat..."
            className="w-full bg-surface-container-high border-none rounded-md py-2.5 px-3 text-xs text-on-surface placeholder:text-outline focus:ring-1 focus:ring-primary outline-none"
          />
          <button
            type="submit"
            disabled={isSubmitting}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-primary p-1 hover:bg-primary/10 rounded-full transition-colors flex items-center justify-center"
          >
            <span className="material-symbols-outlined text-sm">send</span>
          </button>
        </form>
      </div>
    </aside>
  );
}
