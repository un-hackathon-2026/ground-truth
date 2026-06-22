"use client";

import { useState } from "react";
import VisualizationCard from "./VisualizationCard";
import SynthesisEngine from "./SynthesisEngine";

interface Props {
  dataset?: string;
  country?: string;
  name?: string;
}

export default function DashboardClient({ dataset, country, name }: Props) {
  const [activeDataset, setActiveDataset] = useState(dataset);
  const [activeCountry, setActiveCountry] = useState(country);
  const [activeName, setActiveName] = useState(name);

  return (
    <>
      <VisualizationCard
        dataset={activeDataset}
        country={activeCountry}
        name={activeName}
        onManualLoad={(ds, ct) => {
          setActiveDataset(ds);
          setActiveCountry(ct);
          setActiveName(undefined);
        }}
      />
      <SynthesisEngine
        dataset={activeDataset}
        country={activeCountry}
        name={activeName}
      />
    </>
  );
}
