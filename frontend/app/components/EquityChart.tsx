"use client";

import { Card, CardContent, Typography } from "@mui/material";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type EquityPoint = {
  date: string;
  value: number;
};

type EquityChartProps = {
  equityCurve: EquityPoint[];
};

export default function EquityChart({ equityCurve }: EquityChartProps) {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Equity Curve
        </Typography>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={equityCurve}>
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke="#1976d2" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
