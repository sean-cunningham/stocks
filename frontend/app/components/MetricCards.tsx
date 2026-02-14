"use client";

import { Card, CardContent, Stack, Typography } from "@mui/material";
import type { MetricsResponse } from "../apiClient";

type MetricCardsProps = {
  metrics: MetricsResponse;
};

export default function MetricCards({ metrics }: MetricCardsProps) {
  return (
    <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
      <Card sx={{ flex: 1 }}>
        <CardContent>
          <Typography variant="subtitle2">Sharpe</Typography>
          <Typography variant="h6">{metrics.sharpe.toFixed(4)}</Typography>
        </CardContent>
      </Card>
      <Card sx={{ flex: 1 }}>
        <CardContent>
          <Typography variant="subtitle2">Max Drawdown</Typography>
          <Typography variant="h6">{metrics.max_drawdown.toFixed(4)}</Typography>
        </CardContent>
      </Card>
      <Card sx={{ flex: 1 }}>
        <CardContent>
          <Typography variant="subtitle2">Win Rate</Typography>
          <Typography variant="h6">{(metrics.win_rate * 100).toFixed(2)}%</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
