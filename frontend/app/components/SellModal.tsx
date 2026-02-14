"use client";

import { useState } from "react";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField } from "@mui/material";

type SellPayload = {
  ticker: string;
  qty_optional: number | null;
  fees: number;
};

type SellModalProps = {
  open: boolean;
  ticker: string;
  onClose: () => void;
  onSubmit: (payload: SellPayload) => Promise<void>;
};

export default function SellModal({ open, ticker, onClose, onSubmit }: SellModalProps) {
  const [qty, setQty] = useState<string>("");
  const [fees, setFees] = useState<string>("0");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onSubmit({
        ticker,
        qty_optional: qty ? Number(qty) : null,
        fees: fees ? Number(fees) : 0,
      });
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Sell {ticker}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} mt={0.5}>
          <TextField
            label="qty_optional"
            type="number"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            fullWidth
          />
          <TextField label="fees" type="number" value={fees} onChange={(e) => setFees(e.target.value)} fullWidth />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={submitting}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} variant="contained" color="error" disabled={submitting}>
          Submit Sell
        </Button>
      </DialogActions>
    </Dialog>
  );
}
