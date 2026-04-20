"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { artifactUrl } from "@/lib/artifacts";
import type { Heatmap, JobResponse, JobStatusResponse, Prediction } from "@/lib/types";

type LoadState = "idle" | "loading" | "error";

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function toApiDateTime(value: string) {
  return value.replace("T", " ") + ":00";
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

function IconSend() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m4 12 16-8-6 16-3-7-7-1Z" />
      <path d="m11 13 9-9" />
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

function IconDatabase() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5" />
      <path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" />
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

export default function Page() {
  const [history, setHistory] = useState<Prediction[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedHeatmap, setSelectedHeatmap] = useState(0);
  const [historyState, setHistoryState] = useState<LoadState>("idle");
  const [jobState, setJobState] = useState<LoadState>("idle");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [datetime, setDatetime] = useState("2023-04-19T13:00");
  const [rangeStart, setRangeStart] = useState("");
  const [rangeEnd, setRangeEnd] = useState("");
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function stopPolling() {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }

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
      setSelectedId((current) => current ?? data[0]?.prediction_id ?? null);
      setHistoryState("idle");
      return data;
    } catch (error) {
      setHistoryState("error");
      setStatusMessage(error instanceof Error ? error.message : "Could not load history");
      return [];
    }
  }

  useEffect(() => {
    void loadHistory();
    return () => stopPolling();
  }, []);

  const selectedPrediction = useMemo(() => {
    return history.find((prediction) => prediction.prediction_id === selectedId) ?? history[0] ?? null;
  }, [history, selectedId]);

  const filteredHistory = useMemo(() => {
    const start = rangeStart ? new Date(rangeStart).getTime() : null;
    const end = rangeEnd ? new Date(rangeEnd).getTime() : null;

    return history.filter((prediction) => {
      const time = new Date(prediction.prediction_hour).getTime();
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
  }, [history, rangeEnd, rangeStart]);

  const selectedHeatmapData: Heatmap | null =
    selectedPrediction?.heatmaps[selectedHeatmap] ?? selectedPrediction?.heatmaps[0] ?? null;

  function findPredictionForJob(historyData: Prediction[], job: JobStatusResponse | JobResponse) {
    if (job.prediction_id) {
      return historyData.find((prediction) => prediction.prediction_id === job.prediction_id) ?? null;
    }

    return (
      historyData.find((prediction) => {
        return prediction.prediction_hour === job.prediction_hour;
      }) ?? null
    );
  }

  async function fetchJobStatus(jobId: string) {
    const response = await fetch(`/api/jobs/${jobId}`, {
      cache: "no-store"
    });

    const body = (await response.json()) as JobStatusResponse & { detail?: string };
    if (!response.ok) {
      throw new Error(body.detail ?? `Job status request failed with ${response.status}`);
    }
    return body;
  }

  async function pollJobUntilDone(jobId: string, predictionHour: string) {
    stopPolling();

    const poll = async () => {
      try {
        const [job, historyData] = await Promise.all([fetchJobStatus(jobId), loadHistory()]);
        const prediction = findPredictionForJob(historyData, job);

        if (prediction) {
          setSelectedId(prediction.prediction_id);
          setSelectedHeatmap(0);
          setJobState("idle");
          setStatusMessage(`Prediction is ready for ${formatDateTime(prediction.prediction_hour)}.`);
          stopPolling();
          return;
        }

        if (job.status === "failed") {
          setJobState("error");
          setStatusMessage(job.error_message ?? `Prediction job failed for ${formatDateTime(predictionHour)}.`);
          stopPolling();
          return;
        }

        if (job.status === "completed" && job.prediction_id) {
          setJobState("loading");
          setStatusMessage("Prediction finished. Waiting for the saved result to appear in history.");
        } else {
          setJobState("loading");
          setStatusMessage(`Prediction ${job.status} for ${formatDateTime(predictionHour)}. Checking again soon.`);
        }

        pollTimerRef.current = setTimeout(() => {
          void poll();
        }, 4000);
      } catch (error) {
        setJobState("error");
        setStatusMessage(error instanceof Error ? error.message : "Could not check prediction job status");
        stopPolling();
      }
    };

    await poll();
  }

  async function submitJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    stopPolling();
    setJobState("loading");
    setStatusMessage(null);

    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        headers: {
          "content-type": "application/json"
        },
        body: JSON.stringify({
          helioviewer_date: toApiDateTime(datetime)
        })
      });

      const body = (await response.json()) as JobResponse & { detail?: string };
      if (!response.ok) {
        throw new Error(body.detail ?? `Job request failed with ${response.status}`);
      }

      if (body.status === "prediction_exists") {
        setStatusMessage(`Prediction already exists for ${formatDateTime(body.prediction_hour)}.`);
        const historyData = await loadHistory();
        const prediction = findPredictionForJob(historyData, body);
        if (prediction) {
          setSelectedId(prediction.prediction_id);
          setSelectedHeatmap(0);
        }
      } else if (body.status === "job_exists") {
        setStatusMessage(`A ${body.job_status ?? "queued"} job already covers ${formatDateTime(body.prediction_hour)}.`);
        if (body.job_id) {
          await pollJobUntilDone(body.job_id, body.prediction_hour);
          return;
        }
      } else {
        setStatusMessage(`Queued job ${body.job_id} for ${formatDateTime(body.prediction_hour)}.`);
        if (body.job_id) {
          await pollJobUntilDone(body.job_id, body.prediction_hour);
          return;
        }
      }

      setJobState("idle");
      await loadHistory();
    } catch (error) {
      setJobState("error");
      setStatusMessage(error instanceof Error ? error.message : "Could not queue prediction");
    }
  }

  async function fetchLatest() {
    const latestHistory = await loadHistory();
    setSelectedHeatmap(0);
    setSelectedId((current) => latestHistory[0]?.prediction_id ?? current);
  }

  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Hourly HMI flare forecasting</p>
          <h1>Solar Flare Prediction Console</h1>
        </div>
        <form className="jobForm" onSubmit={submitJob}>
          <label htmlFor="prediction-time">Point-in-time</label>
          <input
            id="prediction-time"
            type="datetime-local"
            value={datetime}
            onChange={(event) => setDatetime(event.target.value)}
          />
          <button className="primaryButton" type="submit" disabled={jobState === "loading"}>
            <IconSend />
            <span>{jobState === "loading" ? "Queueing" : "Fetch"}</span>
          </button>
          <button className="iconButton" type="button" onClick={() => void fetchLatest()} title="Fetch latest">
            <IconRefresh />
          </button>
        </form>
      </section>

      {statusMessage ? (
        <section className={`statusBanner ${jobState === "error" || historyState === "error" ? "error" : ""}`}>
          <IconDatabase />
          <span>{statusMessage}</span>
        </section>
      ) : null}

      <section className="workspace">
        <aside className="historyPanel">
          <div className="panelHeader">
            <span>Past History</span>
            <strong>{filteredHistory.length}</strong>
          </div>

          <div className="rangeFilter">
            <label htmlFor="range-start">From</label>
            <input
              id="range-start"
              type="datetime-local"
              value={rangeStart}
              onChange={(event) => setRangeStart(event.target.value)}
            />
            <label htmlFor="range-end">To</label>
            <input
              id="range-end"
              type="datetime-local"
              value={rangeEnd}
              onChange={(event) => setRangeEnd(event.target.value)}
            />
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

          {historyState === "loading" && !history.length ? <div className="emptyState">Loading history</div> : null}
          {historyState === "error" && !history.length ? <div className="emptyState">API unavailable</div> : null}
          {!history.length && historyState === "idle" ? <div className="emptyState">No predictions stored</div> : null}
          {history.length > 0 && filteredHistory.length === 0 ? (
            <div className="emptyState">No predictions in range</div>
          ) : null}

          <div className="historyList">
            {filteredHistory.map((prediction) => {
              const active = prediction.prediction_id === selectedPrediction?.prediction_id;
              return (
                <button
                  key={prediction.prediction_id}
                  className={`historyItem ${active ? "active" : ""}`}
                  type="button"
                  onClick={() => {
                    setSelectedId(prediction.prediction_id);
                    setSelectedHeatmap(0);
                  }}
                >
                  <span className="historyDate">{formatDateTime(prediction.prediction_hour)}</span>
                  <span className={`classPill ${classNameForPrediction(prediction.predicted_class)}`}>
                    {prediction.predicted_class}
                  </span>
                  <strong>{percent(prediction.global_flare_probability)}</strong>
                  <ProbabilityBar value={prediction.global_flare_probability} />
                </button>
              );
            })}
          </div>
        </aside>

        <section className="detailPanel">
          {selectedPrediction ? (
            <>
              <div className="summaryGrid">
                <Metric
                  label="Global probability"
                  value={percent(selectedPrediction.global_flare_probability)}
                  detail={selectedPrediction.predicted_class}
                />
                <Metric
                  label="Prediction hour"
                  value={formatDateTime(selectedPrediction.prediction_hour)}
                  detail={selectedPrediction.prediction_id.slice(0, 8)}
                />
                <Metric
                  label="Localized regions"
                  value={String(selectedPrediction.active_regions.length)}
                  detail={`${selectedPrediction.heatmaps.length} heatmaps`}
                />
              </div>

              <div className="visualGrid">
                <section className="visualStage">
                  <div className="sectionHeader">
                    <div>
                      <span>Full Disk</span>
                      <strong>{formatDateTime(selectedPrediction.date)}</strong>
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

                  <ArtifactImage path={selectedHeatmapData?.image_path} label={selectedHeatmapData?.method_name ?? "Heatmap"} />
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
          ) : jobState === "loading" ? (
            <div className="emptyState large waitingState">
              <IconRefresh />
              <strong>Waiting for prediction results</strong>
              <span>{statusMessage ?? "The worker is processing the requested magnetogram."}</span>
            </div>
          ) : (
            <div className="emptyState large">No prediction selected</div>
          )}
        </section>
      </section>
    </main>
  );
}
