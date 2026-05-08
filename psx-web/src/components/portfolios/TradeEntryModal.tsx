"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  createTransaction,
  fetchPortfolios,
  previewTransaction,
  type TransactionCreate,
  type TransactionPreview,
  type TransactionType,
} from "@/lib/api/portfolios";
import { fetchSecurities, fetchSecurity, type Security } from "@/lib/api/securities";
import { fetchCurrentUser } from "@/lib/api/auth";
import { formatCurrency } from "@/lib/utils/format";

interface Props {
  trigger: React.ReactNode;
  // Optional pre-fill, useful when opened from a stock detail page
  defaultSymbol?: string;
  defaultPrice?: string;
}

const TX_TYPES: { value: TransactionType; label: string }[] = [
  { value: "buy", label: "Buy" },
  { value: "sell", label: "Sell" },
  { value: "dividend", label: "Dividend" },
  { value: "bonus", label: "Bonus" },
  { value: "rights", label: "Rights" },
];

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function TradeEntryModal({ trigger, defaultSymbol, defaultPrice }: Props) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<"form" | "confirm">("form");

  // Form state
  const [txType, setTxType] = useState<TransactionType>("buy");
  const [symbol, setSymbol] = useState(defaultSymbol ?? "");
  const [date, setDate] = useState(todayIso());
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState(defaultPrice ?? "");
  const [brokerage, setBrokerage] = useState("0");
  const [fed, setFed] = useState("0");
  const [cvt, setCvt] = useState("0");
  const [notes, setNotes] = useState("");

  // Preview result
  const [preview, setPreview] = useState<TransactionPreview | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const queryClient = useQueryClient();

  const { data: portfolios } = useQuery({
    queryKey: ["portfolios"],
    queryFn: fetchPortfolios,
    enabled: open,
    staleTime: 60_000,
  });
  const portfolioId = portfolios?.find((p) => p.is_default)?.id ?? portfolios?.[0]?.id;

  // Symbol autocomplete
  const [symbolQuery, setSymbolQuery] = useState("");
  const { data: symbolMatches } = useQuery({
    queryKey: ["securities", "autocomplete", symbolQuery],
    queryFn: () => fetchSecurities({ search: symbolQuery, page_size: 8 }),
    enabled: open && symbolQuery.length >= 1,
    staleTime: 30_000,
  });

  // Shariah-mode: warn when adding a non-compliant stock
  const { data: currentUser } = useQuery({
    queryKey: ["current-user"],
    queryFn: fetchCurrentUser,
    staleTime: 5 * 60_000,
    retry: false,
    enabled: open,
  });
  const { data: selectedSecurity } = useQuery({
    queryKey: ["security", symbol],
    queryFn: () => fetchSecurity(symbol),
    enabled: open && symbol.length >= 1,
    staleTime: 5 * 60_000,
    retry: false,
  });
  const shariahWarning =
    currentUser?.shariah_mode &&
    selectedSecurity &&
    !selectedSecurity.is_kmi_compliant;

  function resetForm() {
    setStep("form");
    setPreview(null);
    setSubmitError(null);
    setTxType("buy");
    setSymbol(defaultSymbol ?? "");
    setDate(todayIso());
    setQuantity("");
    setPrice(defaultPrice ?? "");
    setBrokerage("0");
    setFed("0");
    setCvt("0");
    setNotes("");
    setSymbolQuery("");
  }

  useEffect(() => {
    if (!open) resetForm();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const previewMutation = useMutation({
    mutationFn: (body: TransactionCreate) => {
      if (!portfolioId) throw new Error("No portfolio yet — please retry.");
      return previewTransaction(portfolioId, body);
    },
    onSuccess: (data) => {
      setPreview(data);
      setStep("confirm");
      setSubmitError(null);
    },
    onError: (e: Error) => setSubmitError(e.message),
  });

  const saveMutation = useMutation({
    mutationFn: (body: TransactionCreate) => {
      if (!portfolioId) throw new Error("No portfolio.");
      return createTransaction(portfolioId, body);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["holdings"] });
      queryClient.invalidateQueries({ queryKey: ["portfolios"] });
      setOpen(false);
    },
    onError: (e: Error) => setSubmitError(e.message),
  });

  const body: TransactionCreate = useMemo(
    () => ({
      symbol: symbol.toUpperCase(),
      transaction_type: txType,
      transaction_date: date,
      quantity: quantity || "0",
      price_per_share: price || "0",
      brokerage_pkr: brokerage || "0",
      fed_pkr: fed || "0",
      cvt_pkr: cvt || "0",
      notes: notes || null,
    }),
    [symbol, txType, date, quantity, price, brokerage, fed, cvt, notes],
  );

  const formValid =
    symbol.trim().length > 0 && parseFloat(quantity) > 0 && parseFloat(price) >= 0;

  function handlePreview(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    previewMutation.mutate(body);
  }

  function handleSave() {
    setSubmitError(null);
    saveMutation.mutate(body);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        {step === "form" ? (
          <FormStep
            txType={txType}
            setTxType={setTxType}
            symbol={symbol}
            setSymbol={(s) => {
              setSymbol(s);
              setSymbolQuery(s);
            }}
            symbolMatches={symbolMatches?.items ?? []}
            date={date}
            setDate={setDate}
            quantity={quantity}
            setQuantity={setQuantity}
            price={price}
            setPrice={setPrice}
            brokerage={brokerage}
            setBrokerage={setBrokerage}
            fed={fed}
            setFed={setFed}
            cvt={cvt}
            setCvt={setCvt}
            notes={notes}
            setNotes={setNotes}
            valid={formValid}
            submitting={previewMutation.isPending}
            error={submitError}
            shariahWarning={!!shariahWarning}
            onSubmit={handlePreview}
          />
        ) : preview ? (
          <ConfirmStep
            preview={preview}
            saving={saveMutation.isPending}
            error={submitError}
            onBack={() => setStep("form")}
            onSave={handleSave}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

// ── FormStep ────────────────────────────────────────────────────────────

interface FormStepProps {
  txType: TransactionType;
  setTxType: (v: TransactionType) => void;
  symbol: string;
  setSymbol: (v: string) => void;
  symbolMatches: Security[];
  date: string;
  setDate: (v: string) => void;
  quantity: string;
  setQuantity: (v: string) => void;
  price: string;
  setPrice: (v: string) => void;
  brokerage: string;
  setBrokerage: (v: string) => void;
  fed: string;
  setFed: (v: string) => void;
  cvt: string;
  setCvt: (v: string) => void;
  notes: string;
  setNotes: (v: string) => void;
  valid: boolean;
  submitting: boolean;
  error: string | null;
  shariahWarning?: boolean;
  onSubmit: (e: React.FormEvent) => void;
}

function FormStep(p: FormStepProps) {
  return (
    <form onSubmit={p.onSubmit} className="space-y-4">
      <DialogHeader>
        <DialogTitle>Record a transaction</DialogTitle>
        <DialogDescription>
          We&apos;ll calculate brokerage, FED, CVT and CGT before saving.
        </DialogDescription>
      </DialogHeader>

      {/* Type pills */}
      <div className="flex flex-wrap gap-1.5">
        {TX_TYPES.map((t) => (
          <button
            key={t.value}
            type="button"
            onClick={() => p.setTxType(t.value)}
            className={
              "rounded-md border px-3 py-1.5 text-sm transition " +
              (p.txType === t.value
                ? "border-blue-600 bg-blue-50 text-blue-700"
                : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50")
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Symbol with autocomplete */}
      <div className="relative space-y-1.5">
        <Label htmlFor="symbol">Symbol</Label>
        <Input
          id="symbol"
          value={p.symbol}
          onChange={(e) => p.setSymbol(e.target.value.toUpperCase())}
          placeholder="ENGRO"
          autoComplete="off"
          required
        />
        {p.symbol.length >= 1 && p.symbolMatches.length > 0 && (
          <ul className="absolute left-0 right-0 z-10 mt-1 max-h-48 overflow-y-auto rounded-md border border-gray-200 bg-white shadow-lg">
            {p.symbolMatches.slice(0, 6).map((s) => (
              <li key={s.symbol}>
                <button
                  type="button"
                  onClick={() => p.setSymbol(s.symbol)}
                  className="block w-full px-3 py-1.5 text-left text-sm hover:bg-gray-50"
                >
                  <span className="font-mono font-semibold">{s.symbol}</span>
                  <span className="ml-2 truncate text-gray-500">{s.company_name}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="date">Date</Label>
          <Input
            id="date"
            type="date"
            value={p.date}
            onChange={(e) => p.setDate(e.target.value)}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="qty">
            {p.txType === "dividend" ? "Shares held" : "Quantity"}
          </Label>
          <Input
            id="qty"
            type="number"
            min="0"
            step="0.0001"
            value={p.quantity}
            onChange={(e) => p.setQuantity(e.target.value)}
            required
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="price">
            {p.txType === "dividend"
              ? "Dividend per share (PKR)"
              : "Price per share (PKR)"}
          </Label>
          <Input
            id="price"
            type="number"
            min="0"
            step="0.0001"
            value={p.price}
            onChange={(e) => p.setPrice(e.target.value)}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="brokerage">Brokerage (PKR)</Label>
          <Input
            id="brokerage"
            type="number"
            min="0"
            step="0.01"
            value={p.brokerage}
            onChange={(e) => p.setBrokerage(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="fed">FED (PKR)</Label>
          <Input
            id="fed"
            type="number"
            min="0"
            step="0.01"
            value={p.fed}
            onChange={(e) => p.setFed(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="cvt">CVT (PKR)</Label>
          <Input
            id="cvt"
            type="number"
            min="0"
            step="0.01"
            value={p.cvt}
            onChange={(e) => p.setCvt(e.target.value)}
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="notes">Notes (optional)</Label>
        <Input
          id="notes"
          value={p.notes}
          onChange={(e) => p.setNotes(e.target.value)}
          placeholder="e.g. dividend reinvestment"
        />
      </div>

      {p.shariahWarning && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-800">
          ⚠ This stock is <strong>not KMI-compliant</strong>. Shariah Mode is on
          — you can still record this trade, but it&apos;ll be marked as
          non-compliant in your portfolio.
        </div>
      )}

      {p.error && <p className="text-sm text-red-600">{p.error}</p>}

      <div className="flex justify-end gap-2 pt-2">
        <Button type="submit" disabled={!p.valid || p.submitting}>
          {p.submitting ? "Calculating…" : "Review →"}
        </Button>
      </div>
    </form>
  );
}

// ── ConfirmStep ─────────────────────────────────────────────────────────

interface ConfirmStepProps {
  preview: TransactionPreview;
  saving: boolean;
  error: string | null;
  onBack: () => void;
  onSave: () => void;
}

function ConfirmStep({ preview, saving, error, onBack, onSave }: ConfirmStepProps) {
  const isSell = preview.transaction_type === "sell";
  const net = parseFloat(preview.net_cash_impact_pkr);
  const hasWarnings = preview.warnings.length > 0;

  return (
    <div className="space-y-4">
      <DialogHeader>
        <DialogTitle>Confirm transaction</DialogTitle>
        <DialogDescription>
          Review what hits your portfolio. CGT is computed against open buy lots
          using FIFO.
        </DialogDescription>
      </DialogHeader>

      {hasWarnings && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          {preview.warnings.map((w, i) => (
            <p key={i}>⚠ {w}</p>
          ))}
        </div>
      )}

      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <div className="flex items-center justify-between text-sm">
          <span className="font-mono font-semibold">{preview.symbol}</span>
          <Badge variant={isSell ? "destructive" : "default"}>
            {preview.transaction_type.toUpperCase()}
          </Badge>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          {preview.quantity} × PKR {parseFloat(preview.price_per_share).toFixed(2)}
        </p>

        <dl className="mt-4 space-y-1.5 text-sm">
          <Row label="Gross value" value={formatCurrency(parseFloat(preview.gross_value_pkr))} />
          <Row
            label="Brokerage"
            value={`- ${formatCurrency(parseFloat(preview.brokerage_pkr))}`}
            muted
          />
          <Row
            label="FED"
            value={`- ${formatCurrency(parseFloat(preview.fed_pkr))}`}
            muted
          />
          <Row
            label="CVT"
            value={`- ${formatCurrency(parseFloat(preview.cvt_pkr))}`}
            muted
          />
          {isSell && (
            <Row
              label="CGT (computed)"
              value={`- ${formatCurrency(parseFloat(preview.cgt_pkr))}`}
              muted
            />
          )}
          <div className="my-2 border-t border-gray-200" />
          <Row
            label="Net cash impact"
            value={formatCurrency(net)}
            bold
            valueClass={net >= 0 ? "text-green-700" : "text-red-700"}
          />
        </dl>
      </div>

      {isSell && preview.matched_lots.length > 0 && (
        <div className="rounded-lg border border-gray-200 p-3">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Matched lots (FIFO)
          </h3>
          <ul className="divide-y divide-gray-100 text-xs">
            {preview.matched_lots.map((m, i) => (
              <li key={i} className="grid grid-cols-4 py-1.5">
                <span className="text-gray-500">{m.buy_date}</span>
                <span>
                  {m.quantity} @ {parseFloat(m.buy_price).toFixed(2)}
                </span>
                <span className="text-gray-500">{m.holding_period_days}d</span>
                <span className="text-right font-medium">
                  {parseFloat(m.cgt_pkr) > 0
                    ? formatCurrency(parseFloat(m.cgt_pkr))
                    : "—"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex justify-between gap-2 pt-2">
        <Button type="button" variant="outline" onClick={onBack}>
          ← Back
        </Button>
        <Button
          type="button"
          onClick={onSave}
          disabled={saving || hasWarnings}
        >
          {saving ? "Saving…" : "Save transaction"}
        </Button>
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  bold,
  muted,
  valueClass,
}: {
  label: string;
  value: string;
  bold?: boolean;
  muted?: boolean;
  valueClass?: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <dt className={muted ? "text-gray-500" : "text-gray-700"}>{label}</dt>
      <dd
        className={
          (bold ? "font-semibold text-gray-900" : "text-gray-700") +
          (valueClass ? ` ${valueClass}` : "")
        }
      >
        {value}
      </dd>
    </div>
  );
}
