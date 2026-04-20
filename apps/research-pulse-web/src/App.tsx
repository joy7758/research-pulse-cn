import { startTransition, useEffect, useMemo, useState } from "react";

import "./App.css";
import { Badge } from "./components/Badge";
import { StatusBanner } from "./components/StatusBanner";
import { apiModePlan, loadShellData, mockScenarioOptions } from "./lib/dataSource";
import type { AppPage, DataMode, FrontendShellData, MockScenario } from "./lib/types";
import { HomePage } from "./pages/HomePage";
import { ImportPage } from "./pages/ImportPage";
import { PaperProgressPage } from "./pages/PaperProgressPage";
import { PulseDetailPage } from "./pages/PulseDetailPage";

type NavigationItem = {
  key: AppPage;
  label: string;
  description: string;
};

const navigationItems: NavigationItem[] = [
  {
    key: "home",
    label: "今日 Research Pulse",
    description: "今天该看什么、先处理什么、下一步做什么。",
  },
  {
    key: "import",
    label: "导入 / 导入预览",
    description: "先看清可导入、warning 和 error，再决定是否确认导入。",
  },
  {
    key: "pulse",
    label: "Pulse 详情",
    description: "把今日重点、下一步动作和待补全事项展开到完整结构。",
  },
  {
    key: "progress",
    label: "论文进度",
    description: "围绕待读、略读、精读和下一步动作推进科研阅读。",
  },
];

function formatRefreshTimestamp() {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
}

function App() {
  const [page, setPage] = useState<AppPage>("home");
  const [mode] = useState<DataMode>("mock");
  const [scenario, setScenario] = useState<MockScenario>("default");
  const [shellData, setShellData] = useState<FrontendShellData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showIssuesOnly, setShowIssuesOnly] = useState(false);
  const [importCommitted, setImportCommitted] = useState(false);
  const [draftActionTriggered, setDraftActionTriggered] = useState(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string>("尚未刷新");

  const currentPageMeta = useMemo(
    () => navigationItems.find((item) => item.key === page) ?? navigationItems[0],
    [page],
  );
  const currentScenarioMeta = useMemo(
    () => mockScenarioOptions.find((item) => item.id === scenario) ?? mockScenarioOptions[0],
    [scenario],
  );

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setRefreshing(false);
    setErrorMessage(null);
    setShellData(null);
    setShowIssuesOnly(false);
    setImportCommitted(false);
    setDraftActionTriggered(false);

    void (async () => {
      try {
        const data = await loadShellData(mode, scenario);
        if (cancelled) {
          return;
        }
        setShellData(data);
        setLastRefreshedAt(formatRefreshTimestamp());
      } catch (error) {
        if (cancelled) {
          return;
        }
        setErrorMessage(error instanceof Error ? error.message : String(error));
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [mode, scenario]);

  async function handleRefreshHome() {
    setRefreshing(true);
    setErrorMessage(null);
    try {
      const data = await loadShellData(mode, scenario);
      setShellData(data);
      setLastRefreshedAt(formatRefreshTimestamp());
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setRefreshing(false);
    }
  }

  function navigate(nextPage: AppPage) {
    startTransition(() => {
      setPage(nextPage);
    });
  }

  if (loading) {
    return (
      <main className="shell-root">
        <div className="shell shell-single">
          <section className="panel center-panel">
            <p className="eyebrow">正在载入</p>
            <h1>先把今天的 Pulse 准备好</h1>
            <p className="hero-summary">
              当前使用 {currentScenarioMeta.label} 场景，当前前端壳仍然只读取本地 curated mock JSON。
            </p>
          </section>
        </div>
      </main>
    );
  }

  if (errorMessage || !shellData) {
    return (
      <main className="shell-root">
        <div className="shell shell-single">
          <section className="panel center-panel">
            <p className="eyebrow">当前不可用</p>
            <h1>前端壳还没拿到可读数据</h1>
            <StatusBanner tone="error" title="请先修复 mock mode">
              <p>{errorMessage ?? "当前没有可用的 shell 数据。"}</p>
              <p>你可以先切回默认工作流，再继续验证四页状态和中文文案边界。</p>
            </StatusBanner>
            <div className="hero-actions">
              <button className="button-primary" onClick={() => setScenario("default")} type="button">
                切回默认 mock 场景
              </button>
              <button className="button-secondary" onClick={() => void handleRefreshHome()} type="button">
                重试加载
              </button>
            </div>
          </section>
        </div>
      </main>
    );
  }

  return (
    <main className="shell-root">
      <div className="shell">
        <aside className="sidebar" aria-label="应用侧边栏">
          <div className="brand-card">
            <div className="brand-mark">RP</div>
            <div>
              <p className="eyebrow">minimal web shell</p>
              <h2 className="sidebar-title">Research Pulse</h2>
              <p className="soft-copy">当前只做四页，不做完整产品后台。</p>
            </div>
          </div>

          <section className="sidebar-card">
            <p className="eyebrow">当前模式</p>
            <div className="badge-row">
              <Badge tone="draft">mock mode</Badge>
              <Badge tone="not-sent">api 预留</Badge>
            </div>
            <p className="soft-copy">
              real API mode 仅保留后续内部联调入口，本轮默认不启用。
            </p>
          </section>

          <section className="sidebar-card">
            <div className="section-panel-header">
              <div>
                <p className="eyebrow">状态验证</p>
                <h3>mock 场景</h3>
              </div>
              <Badge tone={scenario === "broken" ? "error" : "preview"}>{currentScenarioMeta.label}</Badge>
            </div>
            <label className="field-label" htmlFor="mock-scenario-select">
              切换空状态、问题状态和异常数据
            </label>
            <select
              id="mock-scenario-select"
              className="field-select"
              value={scenario}
              onChange={(event) => setScenario(event.target.value as MockScenario)}
            >
              {mockScenarioOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
            <p className="soft-copy">{currentScenarioMeta.description}</p>
          </section>

          <nav className="nav-stack" aria-label="页面导航">
            {navigationItems.map((item) => (
              <button
                key={item.key}
                className={`nav-item ${page === item.key ? "nav-item-active" : ""}`}
                onClick={() => navigate(item.key)}
                type="button"
                aria-current={page === item.key ? "page" : undefined}
              >
                <strong>{item.label}</strong>
                <span>{item.description}</span>
              </button>
            ))}
          </nav>

          <section className="sidebar-card">
            <p className="eyebrow">API mode 预留</p>
            <ul className="endpoint-list">
              <li>{apiModePlan.progressList}</li>
              <li>{apiModePlan.importPreview}</li>
              <li>{apiModePlan.importCommit}</li>
              <li>{apiModePlan.progressSummary}</li>
              <li>{apiModePlan.pulseContext}</li>
              <li>{apiModePlan.dailyPulse}</li>
            </ul>
          </section>
        </aside>

        <div className="content" aria-busy={refreshing ? "true" : "false"}>
          <header className="top-bar">
            <div>
              <p className="eyebrow">当前页面</p>
              <h2>{currentPageMeta.label}</h2>
            </div>
            <div className="top-bar-meta">
              <Badge tone="preview">{currentScenarioMeta.label}</Badge>
              <Badge tone="draft">{refreshing ? "刷新中" : "mock 就绪"}</Badge>
              <span>最近刷新：{lastRefreshedAt}</span>
            </div>
          </header>

          {errorMessage ? (
            <StatusBanner tone="error" title="最近一次刷新未成功" eyebrow="当前需处理">
              <p>{errorMessage}</p>
              <p>当前仍保留上一次成功加载的数据，你可以重试刷新或切换回默认场景。</p>
            </StatusBanner>
          ) : null}

          {page === "home" ? (
            <HomePage
              pulse={shellData.researchPulse}
              summary={shellData.progressSummary}
              channelStates={shellData.channelStates}
              lastRefreshedAt={lastRefreshedAt}
              isRefreshing={refreshing}
              scenarioLabel={currentScenarioMeta.label}
              onRefresh={handleRefreshHome}
              onGoImport={() => navigate("import")}
              onGoPulse={() => navigate("pulse")}
            />
          ) : null}

          {page === "import" ? (
            <ImportPage
              preview={shellData.importPreview}
              commit={shellData.importCommit}
              showIssuesOnly={showIssuesOnly}
              committed={importCommitted}
              scenarioLabel={currentScenarioMeta.label}
              onConfirmImport={() => setImportCommitted(true)}
              onToggleIssues={() => setShowIssuesOnly((value) => !value)}
              onBackHome={() => navigate("home")}
            />
          ) : null}

          {page === "pulse" ? (
            <PulseDetailPage
              pulse={shellData.researchPulse}
              channelStates={shellData.channelStates}
              draftActionTriggered={draftActionTriggered}
              scenarioLabel={currentScenarioMeta.label}
              onGenerateOfficialDraft={() => setDraftActionTriggered(true)}
              onBackHome={() => navigate("home")}
            />
          ) : null}

          {page === "progress" ? (
            <PaperProgressPage
              items={shellData.paperProgressItems}
              scenarioLabel={currentScenarioMeta.label}
              onBackHome={() => navigate("home")}
              onGoImport={() => navigate("import")}
              onGoPulse={() => navigate("pulse")}
            />
          ) : null}
        </div>
      </div>
    </main>
  );
}

export default App;
