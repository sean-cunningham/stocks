"use client";

import { useState } from "react";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField } from "@mui/material";

type BuyPayload = {
  ticker: string;
  qty_optional: number | null;
  notional_usd_optional: number | null;
  risk_mode: string | null;
  fees: number;
};

type BuyModalProps = {
  open: boolean;
  ticker: string;
  onClose: () => void;
  onSubmit: (payload: BuyPayload) => Promise<void>;
};

export default function BuyModal({ open, ticker, onClose, onSubmit }: BuyModalProps) {
  const [qty, setQty] = useState<string>("");
  const [notional, setNotional] = useState<string>("");
  const [riskMode, setRiskMode] = useState<string>("moderate");
  const [fees, setFees] = useState<string>("0");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onSubmit({
        ticker,
        qty_optional: qty ? Number(qty) : null,
        notional_usd_optional: notional ? Number(notional) : null,
        risk_mode: riskMode || null,
        fees: fees ? Number(fees) : 0,
      });
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Buy {ticker}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} mt={0.5}>
          <TextField
            label="qty_optional"
            type="number"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            fullWidth
          />
          <TextField
            label="notional_usd_optional"
            type="number"
            value={notional}
            onChange={(e) => setNotional(e.target.value)}
            fullWidth
          />
          <TextField label="risk_mode" value={riskMode} onChange={(e) => setRiskMode(e.target.value)} fullWidth />
          <TextField label="fees" type="number" value={fees} onChange={(e) => setFees(e.target.value)} fullWidth />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={submitting}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} variant="contained" disabled={submitting}>
          Submit Buy
        </Button>
      </DialogActions>
    </Dialog>
  );
}
