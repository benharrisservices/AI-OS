"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

export default function AgentsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: api.agents.list,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Agents</h1>
        <p className="text-sm text-muted-foreground">Registered agent definitions and tools</p>
      </div>
      {isLoading ? (
        <Skeleton className="h-40" />
      ) : !data?.length ? (
        <p className="text-sm text-muted-foreground">No agents configured</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {data.map((a) => (
            <Card key={a.agent_id}>
              <CardHeader>
                <CardTitle className="text-base">{a.name}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">{a.description}</p>
                <div className="flex flex-wrap gap-1">
                  {a.tools.map((t) => (
                    <Badge key={t} variant="outline">
                      {t}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
