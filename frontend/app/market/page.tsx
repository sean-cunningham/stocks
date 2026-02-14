"use client";

import { useMemo, useState } from "react";
import useSWR, { mutate } from "swr";
import { Alert, Button, CircularProgress, Stack, TextField, Typography } from "@mui/material";
import AnalyzeCard from "../components/AnalyzeCard";
import BuyModal from "../components/BuyModal";
import { AnalyzeResponse, fetchJson, getBackendUrl, postJson } from "../apiClient";

const holdingsKey = `${getBackendUrl()}/api/portfolio/active`;

function isValidTicker(ticker: string): boolean {
  return /^[A-Za-z0-9]{1,8}$/.test(ticker);
}

export default function MarketPage() {
  const [tickerInput, setTickerInput] = useState("AAPL");
  const [queryTicker, setQueryTicker] = useState<string>("");
  const [showBuyModal, setShowBuyModal] = useState(false);
  const [submitMessage, setSubmitMessage] = useState("");
  const [submitError, setSubmitError] = useState("");

  const tickerError = useMemo(() => {
    if (!tickerInput) return "Ticker is required.";
    if (!isValidTicker(tickerInput)) return "Ticker must be letters/numbers only, length 1-8.";
    return "";
  }, [tickerInput]);

  const { data, error, isLoading } = useSWR<AnalyzeResponse>(
    queryTicker ? `${getBackendUrl()}/api/analyze/${queryTicker}` : null,
    () => fetchJson<AnalyzeResponse>(`/api/analyze/${queryTicker}`),
    { refreshInterval: 30000 }
  );

  const onAnalyze = () => {
    setSubmitError("");
    setSubmitMessage("");
    if (tickerError) return;
    setQueryTicker(tickerInput.toUpperCase());
  };

  const onBuy = async (payload: {
    ticker: string;
    qty_optional: number | null;
    notional_usd_optional: number | null;
    risk_mode: string | null;
    fees: number;
  }) => {
    setSubmitError("");
    setSubmitMessage("");
    try {
      const response = await postJson<Record<string, unknown>>("/api/portfolio/buy", payload);
      setSubmitMessage(`Buy response: ${JSON.stringify(response)}`);
      await mutate(holdingsKey);
    } catch (e) {
      setSubmitError((e as Error).message || "Buy failed");
      throw e;
    }
  };

  return (
    <Stack spacing={2}>
      <Typography variant="h5">Market</Typography>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <TextField
          label="Ticker"
          value={tickerInput}
          onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
          error={Boolean(tickerError)}
          helperText={tickerError || "Use symbols like AAPL, MSFT, NVDA"}
          fullWidth
        />
        <Button variant="contained" onClick={onAnalyze} disabled={Boolean(tickerError)} sx={{ minWidth: 120 }}>
          Analyze
        </Button>
      </Stack>

      {isLoading && <CircularProgress />}
      {error && (
        <Alert severity="error">
          Unable to reach backend. Ensure FastAPI is running and NEXT_PUBLIC_BACKEND_URL is correct.
        </Alert>
      )}
      {submitError && <Alert severity="error">{submitError}</Alert>}
      {submitMessage && <Alert severity="success">{submitMessage}</Alert>}

      {data && (
        <>
          <AnalyzeCard data={data} />
          <Button variant="contained" onClick={() => setShowBuyModal(true)}>
            Buy
          </Button>
        </>
      )}

      <BuyModal
        open={showBuyModal}
        ticker={(queryTicker || tickerInput).toUpperCase()}
        onClose={() => setShowBuyModal(false)}
        onSubmit={onBuy}
      />
    </Stack>
  );
}
