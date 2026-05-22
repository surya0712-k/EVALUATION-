import { ReportCard } from "../components/report/ReportCard";
import { ScoreTrendChart } from "../components/charts/ScoreTrendChart";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

export function DashboardPage() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        <ReportCard title="Average Score" value="74.2" />
        <ReportCard title="Evaluations" value="128" />
        <ReportCard title="Pass Rate" value="62%" />
      </div>
      <Card>
        <CardHeader><CardTitle>Score trend</CardTitle></CardHeader>
        <CardContent><ScoreTrendChart /></CardContent>
      </Card>
    </div>
  );
}
