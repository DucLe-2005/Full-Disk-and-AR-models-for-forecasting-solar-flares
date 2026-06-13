"use client";

import { useEffect, useMemo, useState } from "react";

import { artifactUrl } from "@/lib/artifacts";
import type { Heatmap, Prediction } from "@/lib/types";

type LoadState = "idle" | "loading" | "error";
type ViewMode = "detail" | "catalog";
type ClassFilter = "all" | "flare" | "non-flare";

function parseDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date;
}

function pad(value: number) {
  return String(value).padStart(2, "0");
}

function formatDateTime(value: string) {
  const date = parseDate(value);
  if (!date) {
    return value;
  }
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ${pad(
    date.getUTCHours()
  )}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())} UTC`;
}

function formatTime(value: string) {
  const date = parseDate(value);
  if (!date) {
    return value;
  }
  return `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())} UTC`;
}

function percent(value: number) {
  return `${Math.round(value * 1000) / 10}%`;
}

function clampProbability(value: number) {
  return Math.max(0, Math.min(1, value));
}

function classNameForPrediction(predictedClass: string) {
  return predictedClass.toLowerCase().includes("non") ? "calm" : "alert";
}

function matchesClassFilter(prediction: Prediction, filter: ClassFilter) {
  if (filter === "all") {
    return true;
  }
  const isNonFlare = prediction.predicted_class.toLowerCase().includes("non");
  return filter === "non-flare" ? isNonFlare : !isNonFlare;
}

function IconRefresh() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M20 6v5h-5" />
      <path d="M4 18v-5h5" />
      <path d="M6.2 9A7 7 0 0 1 18.5 6.5L20 11" />
      <path d="M17.8 15A7 7 0 0 1 5.5 17.5L4 13" />
    </svg>
  );
}

function IconSun() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2" />
      <path d="M12 20v2" />
      <path d="m4.93 4.93 1.41 1.41" />
      <path d="m17.66 17.66 1.41 1.41" />
      <path d="M2 12h2" />
      <path d="M20 12h2" />
      <path d="m6.34 17.66-1.41 1.41" />
      <path d="m19.07 4.93-1.41 1.41" />
    </svg>
  );
}

function IconImage() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3 16 5-5 4 4 2-2 7 6" />
      <path d="M15 9h.01" />
    </svg>
  );
}

function ArtifactImage({
  path,
  label
}: {
  path?: string | null;
  label: string;
}) {
  const url = artifactUrl(path);

  if (!path) {
    return <div className="imagePlaceholder">No image artifact</div>;
  }

  if (!url) {
    return (
      <div className="imagePlaceholder">
        <IconImage />
        <span>{label}</span>
        <code>{path}</code>
      </div>
    );
  }

  return <img className="artifactImage" src={url} alt={label} />;
}

function ProbabilityBar({
  value,
  tone = "flare"
}: {
  value: number;
  tone?: "flare" | "quiet";
}) {
  const width = `${clampProbability(value) * 100}%`;
  return (
    <div className="probabilityTrack" aria-label={`${percent(value)} probability`}>
      <span className={`probabilityFill ${tone}`} style={{ width }} />
    </div>
  );
}

function Metric({
  label,
  value,
  detail
}: {
  label: string;
  value: string;
  detail?: string;
}) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

function PredictionRow({
  prediction,
  active,
  onSelect
}: {
  prediction: Prediction;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button className={`historyItem ${active ? "active" : ""}`} type="button" onClick={onSelect}>
      <span className="historyDate">{formatDateTime(prediction.requested_at).replace(" UTC", "")}</span>
      <span className={`classPill ${classNameForPrediction(prediction.predicted_class)}`}>
        {prediction.predicted_class}
      </span>
      <strong>{percent(prediction.global_flare_probability)}</strong>
      <small>{formatTime(prediction.requested_at)}</small>
      <ProbabilityBar value={prediction.global_flare_probability} />
    </button>
  );
}

function PredictionCard({
  prediction,
  active,
  onSelect
}: {
  prediction: Prediction;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button className={`catalogCard ${active ? "active" : ""}`} type="button" onClick={onSelect}>
      <ArtifactImage path={prediction.full_disk_image_url} label="Full-disk HMI image" />
      <div className="catalogBody">
        <div>
          <strong>{formatDateTime(prediction.requested_at)}</strong>
          <span className={`classPill ${classNameForPrediction(prediction.predicted_class)}`}>
            {prediction.predicted_class}
          </span>
        </div>
        <span>{percent(prediction.global_flare_probability)}</span>
        <ProbabilityBar value={prediction.global_flare_probability} />
      </div>
    </button>
  );
}

export default function Page() {
  const [history, setHistory] = useState<Prediction[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedHeatmap, setSelectedHeatmap] = useState(0);
  const [historyState, setHistoryState] = useState<LoadState>("idle");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [rangeStart, setRangeStart] = useState("");
  const [rangeEnd, setRangeEnd] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("detail");
  const [classFilter, setClassFilter] = useState<ClassFilter>("all");
  const [lastLoadedAt, setLastLoadedAt] = useState<string | null>(null);

  async function loadHistory() {
    setHistoryState("loading");
    setStatusMessage(null);

    try {
      const response = await fetch("/api/history", {
        cache: "no-store"
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail ?? `History request failed with ${response.status}`);
      }

      const data = (await response.json()) as Prediction[];
      setHistory(data);
      setLastLoadedAt(new Date().toISOString());
      setSelectedId((current) => {
        if (current && data.some((prediction) => prediction.prediction_id === current)) {
          return current;
        }
        return data[0]?.prediction_id ?? null;
      });
      setHistoryState("idle");
      return data;
    } catch (error) {
      setHistoryState("error");
      const message = error instanceof Error ? error.message : "Could not load history";
      setStatusMessage(message === "fetch failed" ? "Backend API unavailable" : message);
      return [];
    }
  }

  useEffect(() => {
    void loadHistory();
  }, []);

  const filteredHistory = useMemo(() => {
    const start = rangeStart ? new Date(rangeStart).getTime() : null;
    const end = rangeEnd ? new Date(rangeEnd).getTime() : null;

    return history.filter((prediction) => {
      if (!matchesClassFilter(prediction, classFilter)) {
        return false;
      }
      const time = new Date(prediction.requested_at).getTime();
      if (Number.isNaN(time)) {
        return true;
      }
      if (start !== null && time < start) {
        return false;
      }
      if (end !== null && time > end) {
        return false;
      }
      return true;
    });
  }, [classFilter, history, rangeEnd, rangeStart]);

  const selectedPrediction = useMemo(() => {
    const visibleSelection = filteredHistory.find((prediction) => prediction.prediction_id === selectedId);
    return visibleSelection ?? filteredHistory[0] ?? null;
  }, [filteredHistory, selectedId]);

  const selectedHeatmapData: Heatmap | null =
    selectedPrediction?.heatmaps[selectedHeatmap] ?? selectedPrediction?.heatmaps[0] ?? null;

  function selectPrediction(prediction: Prediction) {
    setSelectedId(prediction.prediction_id);
    setSelectedHeatmap(0);
    setViewMode("detail");
  }

  return (
    <main className="appShell">
      <header className="topbar">
        <div className="brand">
          <IconSun />
          <h1>Solar Flare Prediction Records</h1>
        </div>
        <div className="toolbar" aria-label="Prediction controls">
          <span className="lastUpdated">
            {lastLoadedAt ? `Last updated: ${formatTime(lastLoadedAt)}` : historyState === "error" ? "Last updated: unavailable" : "Last updated: --"}
          </span>
          <button className="refreshButton" type="button" onClick={() => void loadHistory()}>
            <IconRefresh />
            <span>Refresh</span>
          </button>
          <div className="viewToggle" role="tablist" aria-label="View mode">
            <button
              className={viewMode === "detail" ? "selected" : ""}
              type="button"
              onClick={() => setViewMode("detail")}
            >
              Detail
            </button>
            <button
              className={viewMode === "catalog" ? "selected" : ""}
              type="button"
              onClick={() => setViewMode("catalog")}
            >
              Catalog
            </button>
          </div>
        </div>
      </header>

      {statusMessage ? (
        <section className={`statusBanner ${historyState === "error" ? "error" : ""}`}>
          <span>{statusMessage}</span>
        </section>
      ) : null}

      <section className="workspace">
        <aside className="historyPanel">
          <div className="rangeFilter">
            <label>Date range (UTC)</label>
            <div className="dateRange">
              <input
                id="range-start"
                type="datetime-local"
                value={rangeStart}
                onChange={(event) => setRangeStart(event.target.value)}
              />
              <span>-</span>
              <input
                id="range-end"
                type="datetime-local"
                value={rangeEnd}
                onChange={(event) => setRangeEnd(event.target.value)}
              />
            </div>
            <label htmlFor="class-filter">Class filter</label>
            <select id="class-filter" value={classFilter} onChange={(event) => setClassFilter(event.target.value as ClassFilter)}>
              <option value="all">All</option>
              <option value="flare">Flare</option>
              <option value="non-flare">Non-flare</option>
            </select>
            <button
              type="button"
              onClick={() => {
                setRangeStart("");
                setRangeEnd("");
              }}
            >
              Clear range
            </button>
          </div>

          <div className="recordsCount">{filteredHistory.length} records</div>

          {historyState === "loading" && !history.length ? <div className="emptyState">Loading predictions</div> : null}
          {historyState === "error" && !history.length ? <div className="emptyState">API unavailable</div> : null}
          {!history.length && historyState === "idle" ? <div className="emptyState">No predictions stored</div> : null}
          {history.length > 0 && filteredHistory.length === 0 ? (
            <div className="emptyState">No predictions in range</div>
          ) : null}

          <div className="historyList">
            {filteredHistory.map((prediction) => (
              <PredictionRow
                key={prediction.prediction_id}
                prediction={prediction}
                active={prediction.prediction_id === selectedPrediction?.prediction_id}
                onSelect={() => selectPrediction(prediction)}
              />
            ))}
          </div>
        </aside>

        {viewMode === "catalog" ? (
          <section className="catalogPanel">
            {filteredHistory.length ? (
              <div className="catalogGrid">
                {filteredHistory.map((prediction) => (
                  <PredictionCard
                    key={prediction.prediction_id}
                    prediction={prediction}
                    active={prediction.prediction_id === selectedPrediction?.prediction_id}
                    onSelect={() => selectPrediction(prediction)}
                  />
                ))}
              </div>
            ) : (
              <div className="emptyState large">No predictions to display</div>
            )}
          </section>
        ) : (
          <section className="detailPanel">
            {selectedPrediction ? (
              <>
                <div className="eventHeader">
                  <div className="eventTitle">
                    <strong>{formatDateTime(selectedPrediction.requested_at)}</strong>
                    <span className={`classPill ${classNameForPrediction(selectedPrediction.predicted_class)}`}>
                      {selectedPrediction.predicted_class}
                    </span>
                    <span>{percent(selectedPrediction.global_flare_probability)}</span>
                  </div>
                  <div className="eventMeta">
                    <span>requested_at</span>
                    <strong>{formatDateTime(selectedPrediction.requested_at)}</strong>
                  </div>
                </div>
                <div className="summaryGrid">
                  <Metric
                    label="Flare probability"
                    value={percent(selectedPrediction.global_flare_probability)}
                  />
                  <Metric
                    label="Predicted class"
                    value={selectedPrediction.predicted_class}
                    detail={`id ${selectedPrediction.prediction_id.slice(0, 8)}`}
                  />
                  <Metric
                    label="Localized regions"
                    value={String(selectedPrediction.active_regions.length)}
                  />
                  <Metric label="Heatmaps" value={String(selectedPrediction.heatmaps.length)} />
                  <Metric label="Data source" value="SDO / HMI" />
                </div>

                <div className="visualGrid">
                  <section className="visualStage">
                    <div className="sectionHeader">
                      <div>
                        <span>Full-Disk Magnetogram (HMI)</span>
                        <strong>{formatDateTime(selectedPrediction.requested_at)}</strong>
                      </div>
                      <span className={`classPill ${classNameForPrediction(selectedPrediction.predicted_class)}`}>
                        {selectedPrediction.predicted_class}
                      </span>
                    </div>
                    <ArtifactImage path={selectedPrediction.full_disk_image_url} label="Full-disk HMI image" />
                  </section>

                  <section className="visualStage">
                    <div className="sectionHeader">
                      <div>
                        <span>Attribution</span>
                        <strong>{selectedHeatmapData?.method_name ?? "No heatmap"}</strong>
                      </div>
                    </div>

                    {selectedPrediction.heatmaps.length ? (
                      <div className="heatmapTabs" role="tablist">
                        {selectedPrediction.heatmaps.map((heatmap, index) => (
                          <button
                            key={`${heatmap.method_name}-${heatmap.image_path}`}
                            className={index === selectedHeatmap ? "selected" : ""}
                            type="button"
                            onClick={() => setSelectedHeatmap(index)}
                          >
                            {heatmap.method_name}
                          </button>
                        ))}
                      </div>
                    ) : null}

                    <ArtifactImage
                      path={selectedHeatmapData?.image_path}
                      label={selectedHeatmapData?.method_name ?? "Heatmap"}
                    />
                  </section>
                </div>

                <section className="regionsSection">
                  <div className="sectionHeader">
                    <div>
                      <span>Active Regions</span>
                      <strong>Localized probabilities</strong>
                    </div>
                  </div>

                  {selectedPrediction.active_regions.length ? (
                    <div className="regionGrid">
                      {selectedPrediction.active_regions.map((region) => (
                        <article className="regionCard" key={`${selectedPrediction.prediction_id}-${region.rank}`}>
                          <ArtifactImage path={region.image_path} label={`Active region ${region.rank}`} />
                          <div className="regionBody">
                            <div className="regionTitle">
                              <strong>Region {region.rank}</strong>
                              <span>{percent(region.probability)}</span>
                            </div>
                            <ProbabilityBar value={region.probability} tone="quiet" />
                            <dl>
                              <div>
                                <dt>Heatmap</dt>
                                <dd>{region.heatmap_score == null ? "n/a" : region.heatmap_score.toFixed(4)}</dd>
                              </div>
                              <div>
                                <dt>Box</dt>
                                <dd>{region.bbox_original?.join(", ") ?? "n/a"}</dd>
                              </div>
                            </dl>
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className="emptyState">No active regions saved</div>
                  )}
                </section>
              </>
            ) : (
              <div className="emptyState large">No prediction selected</div>
            )}
          </section>
        )}
      </section>
    </main>
  );
}
