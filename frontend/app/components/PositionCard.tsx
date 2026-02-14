"use client";

import { Alert, Button, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import type { ActivePosition } from "../apiClient";

type PositionCardProps = {
  position: ActivePosition;
  onSell: (ticker: string) => void;
};

export default function PositionCard({ position, onSell }: PositionCardProps) {
  const pnlPct = (position.unrealized_pnl_pct * 100).toFixed(2);
  const rec = position.last_decision?.rec || "N/A";
  const score = position.last_decision?.signal_score;
  const prob = position.last_decision?.prob_outperform_90d;

  return (
    <Card sx={{ width: "100%" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1} flexWrap="wrap">
          <Typography variant="h6">{position.ticker}</Typography>
          {position.sell_trigger && <Chip color="warning" label="Sell Trigger" />}
        </Stack>

        <Stack spacing={0.5} mt={1.5}>
          <Typography variant="body2">Net Qty: {position.net_qty.toFixed(4)}</Typography>
          <Typography variant="body2">Avg Cost: ${position.avg_cost.toFixed(2)}</Typography>
          <Typography variant="body2">Current Price: ${position.current_price.toFixed(2)}</Typography>
          <Typography variant="body2">Unrealized PnL: {pnlPct}%</Typography>
          <Typography variant="body2">Last Rec: {rec}</Typography>
          <Typography variant="body2">Signal Score: {score !== undefined ? score.toFixed(3) : "N/A"}</Typography>
          <Typography variant="body2">
            Prob Outperform 90d: {prob !== undefined ? prob.toFixed(3) : "N/A"}
          </Typography>
        </Stack>

        {position.sell_trigger && (
          <Alert severity="warning" sx={{ mt: 1.5 }}>
            {position.sell_reason || "Sell conditions triggered."}
          </Alert>
        )}

        <Stack direction="row" justifyContent="flex-end" mt={2}>
          <Button variant="contained" color="error" onClick={() => onSell(position.ticker)}>
            Sell
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}
