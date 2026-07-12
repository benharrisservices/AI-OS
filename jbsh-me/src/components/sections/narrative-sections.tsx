"use client";

import { NarratedSection } from "@/components/sections/narrated-section";
import { narratedChapters } from "@/content/chapters";

function Narrative({ id }: { id: string }) {
  const chapter = narratedChapters[id];
  return (
    <NarratedSection
      id={chapter.id}
      number={chapter.number}
      title={chapter.title}
      subtitle={chapter.subtitle}
      lines={[...chapter.lines]}
    />
  );
}

export const IdentitySection = () => <Narrative id="identity" />;
export const FreedomSection = () => <Narrative id="freedom" />;
export const LearningSection = () => <Narrative id="learning" />;
export const HealthSection = () => <Narrative id="health" />;
export const MoneySection = () => <Narrative id="money" />;
export const BusinessSection = () => <Narrative id="business" />;
export const TechnologySection = () => <Narrative id="technology" />;
export const AISection = () => <Narrative id="ai" />;
export const LeverageSection = () => <Narrative id="leverage" />;
