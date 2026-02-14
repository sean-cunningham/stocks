"use client";

import useSWR from "swr";
import { Alert, CircularProgress, Stack, Typography } from "@mui/material";
import { MetricsResponse, fetchJson, getBackendUrl } from "../apiClient";
import MetricCards from "../components/MetricCards";
import EquityChart from "../components/EquityChart";

export default function MetricsPage() {
  const { data, error, isLoading } = useSWR<MetricsResponse>(
    `${getBackendUrl()}/api/metrics`,
    () => fetchJson<MetricsResponse>("/api/metrics"),
    { refreshInterval: 30000 }
  );

  return (
    <Stack spacing={2}>
      <Typography variant="h5">Metrics</Typography>
      {isLoading && <CircularProgress />}
      {error && (
        <Alert severity="error">
          Unable to reach backend. Ensure FastAPI is running and NEXT_PUBLIC_BACKEND_URL is correct.
        </Alert>
      )}
      {data && (
        <>
          <MetricCards metrics={data} />
          <EquityChart equityCurve={data.equity_curve} />
        </>
      )}
    </Stack>
  );
}
