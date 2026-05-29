"use client";

import { motion } from "framer-motion";
import { Moon, Star, Snowflake, Flower2, Book, Church, Sun } from "lucide-react";

interface SeasonalEvent {
  name: string;
  type: string;
  impact: string;
  impactValue: number;
  icon: string;
  startDate?: string;
  endDate?: string;
}

interface SeasonalEventCardProps {
  events: SeasonalEvent[];
  delay?: number;
}

const iconMap: Record<string, React.ReactNode> = {
  moon: <Moon className="w-4 h-4" />,
  star: <Star className="w-4 h-4" />,
  snow: <Snowflake className="w-4 h-4" />,
  flower: <Flower2 className="w-4 h-4" />,
  book: <Book className="w-4 h-4" />,
  cross: <Church className="w-4 h-4" />,
  sun: <Sun className="w-4 h-4" />,
};

const typeColors: Record<string, string> = {
  ramadan: "border-emerald-500/20 bg-emerald-500/5",
  eid: "border-gold-500/20 bg-gold-500/5",
  seasonal: "border-blue-500/20 bg-blue-500/5",
  climate: "border-purple-500/20 bg-purple-500/5",
  christian: "border-rose-500/20 bg-rose-500/5",
};

const impactColors: Record<string, string> = {
  ارتفاع: "text-emerald-400 bg-emerald-500/10",
  "ارتفاع حاد": "text-emerald-400 bg-emerald-500/15",
  انخفاض: "text-red-400 bg-red-500/10",
};

export default function SeasonalEventCard({ events, delay = 0 }: SeasonalEventCardProps) {
  return (
    <div className="space-y-3">
      {events.map((event, i) => (
        <motion.div
          key={event.name}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: delay + i * 0.08, ease: [0.25, 0.25, 0, 1] }}
          className={`glass-sm rounded-xl p-4 border ${
            typeColors[event.type] || "border-white/5"
          } flex items-center justify-between`}
        >
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${
              typeColors[event.type]?.replace("border", "bg").replace("/20", "/10") || "bg-white/5"
            }`}>
              {iconMap[event.icon] || <Star className="w-4 h-4 text-gray-400" />}
            </div>
            <div>
              <p className="text-sm font-medium text-white">{event.name}</p>
              <span className="text-[10px] text-gray-500">
                {event.startDate && event.endDate
                  ? `${event.startDate} → ${event.endDate}`
                  : event.type}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-md ${
              impactColors[event.impact] || "text-gray-400 bg-white/5"
            }`}>
              {event.impactValue > 0 ? "+" : ""}{event.impactValue}%
            </span>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
