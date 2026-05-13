"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createStrategy,
  deleteStrategy,
  fetchMyStrategies,
  fetchPublicStrategies,
  forkStrategy,
  type StrategyRule,
  type UserStrategy,
} from "@/lib/api/community";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { GitFork, Globe, Lock, Trash2 } from "lucide-react";

const TEMPLATE_RULES: Record<string, StrategyRule> = {
  rsi_oversold: {
    entry: {
      operator: "<",
      left: { kind: "indicator", name: "rsi", period: 14 },
      right: { kind: "constant", value: 30 },
    },
    exit: {
      any_of: [
        {
          operator: ">",
          left: { kind: "indicator", name: "rsi", period: 14 },
          right: { kind: "constant", value: 70 },
        },
        { kind: "holding_days_gt", value: 30 },
      ],
    },
  },
  price_above_sma200: {
    entry: {
      operator: ">",
      left: { kind: "price" },
      right: { kind: "indicator", name: "sma", period: 200 },
    },
    exit: {
      operator: "<",
      left: { kind: "price" },
      right: { kind: "indicator", name: "sma", period: 200 },
    },
  },
};

export default function StrategiesPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Strategy builder</h1>
        <p className="mt-1 text-sm text-gray-500">
          Build a custom backtest rule. Save it private, or share it publicly
          for others to fork.
        </p>
      </div>

      <Tabs defaultValue="mine">
        <TabsList>
          <TabsTrigger value="mine">My strategies</TabsTrigger>
          <TabsTrigger value="public">Marketplace</TabsTrigger>
          <TabsTrigger value="new">New</TabsTrigger>
        </TabsList>
        <TabsContent value="mine">
          <MyList />
        </TabsContent>
        <TabsContent value="public">
          <PublicList />
        </TabsContent>
        <TabsContent value="new">
          <NewStrategyForm />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function MyList() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["strategies", "mine"],
    queryFn: fetchMyStrategies,
  });
  const remove = useMutation({
    mutationFn: (id: string) => deleteStrategy(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["strategies", "mine"] }),
  });

  if (isLoading || !data) return <div className="h-32 animate-pulse rounded-lg bg-gray-100" />;
  if (data.length === 0)
    return <p className="py-6 text-sm text-gray-500">No strategies yet. Create one in the New tab.</p>;

  return (
    <ul className="space-y-2">
      {data.map((s) => (
        <li
          key={s.id}
          className="flex items-start justify-between gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm"
        >
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-gray-900">{s.name}</h3>
              {s.is_public ? (
                <Globe className="h-3.5 w-3.5 text-blue-600" />
              ) : (
                <Lock className="h-3.5 w-3.5 text-gray-400" />
              )}
              {s.forked_from && (
                <span className="text-[10px] uppercase tracking-wider text-gray-400">forked</span>
              )}
            </div>
            {s.description && (
              <p className="mt-1 text-xs text-gray-600">{s.description}</p>
            )}
            <pre className="mt-2 overflow-x-auto rounded bg-gray-50 p-2 text-[10px] text-gray-700">
              {JSON.stringify(s.rules, null, 2)}
            </pre>
          </div>
          <button
            type="button"
            onClick={() => remove.mutate(s.id)}
            disabled={remove.isPending}
            className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
            aria-label={`Delete strategy: ${s.name}`}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </li>
      ))}
    </ul>
  );
}

function PublicList() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["strategies", "public"],
    queryFn: fetchPublicStrategies,
  });
  const fork = useMutation({
    mutationFn: (id: string) => forkStrategy(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["strategies", "mine"] }),
  });

  if (isLoading || !data) return <div className="h-32 animate-pulse rounded-lg bg-gray-100" />;
  if (data.length === 0)
    return (
      <p className="py-6 text-sm text-gray-500">
        Nothing public yet. Be the first to publish a strategy.
      </p>
    );

  return (
    <ul className="space-y-2">
      {data.map((s) => (
        <li
          key={s.id}
          className="flex items-start justify-between gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm"
        >
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-gray-900">{s.name}</h3>
            {s.description && <p className="mt-1 text-xs text-gray-600">{s.description}</p>}
          </div>
          <Button
            variant="outline"
            onClick={() => fork.mutate(s.id)}
            disabled={fork.isPending}
            className="gap-1"
          >
            <GitFork className="h-4 w-4" />
            Fork
          </Button>
        </li>
      ))}
    </ul>
  );
}

function NewStrategyForm() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [template, setTemplate] = useState<keyof typeof TEMPLATE_RULES>("rsi_oversold");
  const [rulesText, setRulesText] = useState(
    JSON.stringify(TEMPLATE_RULES.rsi_oversold, null, 2),
  );
  const [isPublic, setIsPublic] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () => {
      let parsed: StrategyRule;
      try {
        parsed = JSON.parse(rulesText);
      } catch {
        throw new Error("Rules must be valid JSON.");
      }
      return createStrategy({ name, description, rules: parsed, is_public: isPublic });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategies", "mine"] });
      setName("");
      setDescription("");
    },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <form
      className="space-y-3 rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
      onSubmit={(e) => {
        e.preventDefault();
        setError(null);
        create.mutate();
      }}
    >
      <div className="space-y-1.5">
        <Label htmlFor="strat-name">Name</Label>
        <Input
          id="strat-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="My RSI dip-buyer"
          required
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="strat-desc">Description (optional)</Label>
        <Input
          id="strat-desc"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="strat-template">Start from template</Label>
        <select
          id="strat-template"
          value={template}
          onChange={(e) => {
            const t = e.target.value as keyof typeof TEMPLATE_RULES;
            setTemplate(t);
            setRulesText(JSON.stringify(TEMPLATE_RULES[t], null, 2));
          }}
          className="w-full rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
        >
          <option value="rsi_oversold">RSI &lt; 30 buy / RSI &gt; 70 exit (or 30d stop)</option>
          <option value="price_above_sma200">Price &gt; SMA-200 long-only trend filter</option>
        </select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="strat-rules">Rules (JSON)</Label>
        <textarea
          id="strat-rules"
          value={rulesText}
          onChange={(e) => setRulesText(e.target.value)}
          rows={14}
          className="w-full rounded-md border border-gray-300 bg-white p-2 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-blue-600"
        />
        <p className="text-xs text-gray-500">
          Supported indicators: rsi, sma, ema, macd_histogram, stochastic_k,
          atr, volume. Operators: &lt;, &lt;=, &gt;, &gt;=, ==. Wrap clauses
          in <code>all_of</code>/<code>any_of</code>. Use{" "}
          <code>{"{kind: 'holding_days_gt', value: 30}"}</code> for time stops.
        </p>
      </div>

      <label className="flex items-center gap-2 text-sm text-gray-700">
        <input
          type="checkbox"
          checked={isPublic}
          onChange={(e) => setIsPublic(e.target.checked)}
          className="h-4 w-4"
        />
        Publish to marketplace
      </label>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Button type="submit" disabled={!name.trim() || create.isPending}>
        {create.isPending ? "Saving…" : "Save strategy"}
      </Button>
    </form>
  );
}
