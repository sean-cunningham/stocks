"use client";

import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import type { AnalyzeResponse } from "../apiClient";

type AnalyzeCardProps = {
  data: AnalyzeResponse;
};

function valueText(value: unknown): string {
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return `${value.length} item(s)`;
  if (value && typeof value === "object") return "Object";
  return "N/A";
}

export default function AnalyzeCard({ data }: AnalyzeCardProps) {
  const evidence = data.evidence_packet;
  const decision = data.llm_decision;

  return (
    <Card>
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" mb={1}>
          <Typography variant="h6">Analysis</Typography>
          <Chip label={`Rec: ${decision.rec}`} color="primary" />
          <Chip label={`Signal: ${decision.signal_score.toFixed(3)}`} />
          <Chip label={`Prob90d: ${decision.prob_outperform_90d.toFixed(3)}`} />
        </Stack>

        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1">Evidence Summary</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Stack spacing={0.5}>
              {Object.entries(evidence).map(([key, value]) => (
                <Typography key={key} variant="body2">
                  {key}: {valueText(value)}
                </Typography>
              ))}
            </Stack>
          </AccordionDetails>
        </Accordion>

        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1">LLM Decision Details</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Stack spacing={0.5}>
              <Typography variant="body2">Horizon Days: {decision.horizon_days}</Typography>
              <Typography variant="body2">Drivers: {decision.key_drivers.join("; ") || "N/A"}</Typography>
              <Typography variant="body2">Risks: {decision.key_risks.join("; ") || "N/A"}</Typography>
              <Typography variant="body2">
                Disconfirming Evidence: {decision.disconfirming_evidence.join("; ") || "N/A"}
              </Typography>
              <Typography variant="body2">
                What Changed: {decision.what_changed_since_last?.join("; ") || "N/A"}
              </Typography>
              <Typography variant="body2">Exit Triggers: {decision.exit_triggers.join("; ") || "N/A"}</Typography>
            </Stack>
          </AccordionDetails>
        </Accordion>
      </CardContent>
    </Card>
  );
}
