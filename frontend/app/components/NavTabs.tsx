"use client";

import { useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Box, Tab, Tabs } from "@mui/material";

const routes = [
  { label: "Holdings", value: "/holdings" },
  { label: "Market", value: "/market" },
  { label: "Metrics", value: "/metrics" },
];

export default function NavTabs() {
  const pathname = usePathname();
  const router = useRouter();

  const currentValue = useMemo(() => {
    const match = routes.find((item) => pathname.startsWith(item.value));
    return match?.value || false;
  }, [pathname]);

  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
      <Tabs
        value={currentValue}
        onChange={(_, value: string) => router.push(value)}
        variant="fullWidth"
        aria-label="Navigation tabs"
      >
        {routes.map((item) => (
          <Tab key={item.value} label={item.label} value={item.value} />
        ))}
      </Tabs>
    </Box>
  );
}
