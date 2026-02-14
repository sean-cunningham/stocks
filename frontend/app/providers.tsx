"use client";

import type { ReactNode } from "react";
import { Box, Container, CssBaseline, ThemeProvider, Typography, createTheme } from "@mui/material";
import NavTabs from "./components/NavTabs";

const theme = createTheme({
  palette: {
    mode: "light",
  },
});

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="md" sx={{ py: 2, minHeight: "100vh", display: "flex", flexDirection: "column" }}>
        <NavTabs />
        <Box sx={{ flex: 1 }}>{children}</Box>
        <Box component="footer" sx={{ mt: 3, py: 1.5, borderTop: "1px solid", borderColor: "divider" }}>
          <Typography variant="caption" color="text.secondary">
            Paper trading / informational only. Not investment advice.
          </Typography>
        </Box>
      </Container>
    </ThemeProvider>
  );
}
