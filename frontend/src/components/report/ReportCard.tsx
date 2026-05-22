import { motion } from "framer-motion";

import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

type Props = {
  title: string;
  value: string;
};

export function ReportCard({ title, value }: Props) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm text-slate-500">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold text-slate-900">{value}</p>
        </CardContent>
      </Card>
    </motion.div>
  );
}
