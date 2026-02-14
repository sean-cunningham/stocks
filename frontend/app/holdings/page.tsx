"use client";

import { useState } from "react";
import useSWR, { mutate } from "swr";
import { Alert, CircularProgress, Stack, Typography } from "@mui/material";
import PositionCard from "../components/PositionCard";
import SellModal from "../components/SellModal";
import { ActivePosition, fetchJson, getBackendUrl, postJson } from "../apiClient";

const holdingsKey = `${getBackendUrl()}/api/portfolio/active`;

export default function HoldingsPage() {
  const [selectedTicker, setSelectedTicker] = useState<string>("");
  const [submitMessage, setSubmitMessage] = useState<string>("");
  const [submitError, setSubmitError] = useState<string>("");

  const { data, error, isLoading } = useSWR<ActivePosition[]>(
    holdingsKey,
    () => fetchJson<ActivePosition[]>("/api/portfolio/active"),
    { refreshInterval: 15000 }
  );

  const handleSell = async (payload: { ticker: string; qty_optional: number | null; fees: number }) => {
    setSubmitError("");
    setSubmitMessage("");
    try {
      const res = await postJson<{ status: string; ticker: string; qty: number; price: number }>(
        "/api/portfolio/sell",
        payload
      );
      setSubmitMessage(`Sold ${res.qty} ${res.ticker} @ ${res.price}`);
      await mutate(holdingsKey);
    } catch (e) {
      setSubmitError((e as Error).message || "Sell failed");
    }
  };

  return (
    <Stack spacing={2}>
      <Typography variant="h5">Holdings</Typography>
      {isLoading && <CircularProgress />}
      {error && (
        <Alert severity="error">
          Unable to reach backend. Ensure FastAPI is running and NEXT_PUBLIC_BACKEND_URL is correct.
        </Alert>
      )}
      {submitError && <Alert severity="error">{submitError}</Alert>}
      {submitMessage && <Alert severity="success">{submitMessage}</Alert>}

      {(data || []).map((position) => (
        <PositionCard key={position.ticker} position={position} onSell={(ticker) => setSelectedTicker(ticker)} />
      ))}

      <SellModal
        open={Boolean(selectedTicker)}
        ticker={selectedTicker}
        onClose={() => setSelectedTicker("")}
        onSubmit={handleSell}
      />
    </Stack>
  );
}
