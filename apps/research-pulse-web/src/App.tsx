import { startTransition, useCallback, useEffect, useMemo, useState } from "react";

import "./App.css";
import { Badge } from "./components/Badge";
import { StatusBanner } from "./components/StatusBanner";
import { apiModePlan, loadShellData } from "./lib/dataSource";
import type { AppPage, DataMode, FrontendShellData } from "./lib/types";
import { HomePage } from "./pages/HomePage";
import { ImportPage } from "./pages/ImportPage";
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
];

function App() {
  const [page, setPage] = useState<AppPage>("home");
  const [mode] = useState<DataMode>("mock");
  const [shellData, setShellData] = useState<FrontendShellData | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showIssuesOnly, setShowIssuesOnly] = useState(false);
  const [importCommitted, setImportCommitted] = useState(false);
  const [draftActionTriggered, setDraftActionTriggered] = useState(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string>("尚未刷新");

  const hydrateData = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await loadShellData(mode);
      setShellData(data);
      setLastRefreshedAt(
        new Intl.DateTimeFormat("zh-CN", {
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        }).format(new Date()),
      );
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setLoading(false);
    }
  }, [mode]);

  useEffect(() => {
    void hydrateData();
  }, [hydrateData]);

  const currentPageMeta = useMemo(
    () => navigationItems.find((item) => item.key === page) ?? navigationItems[0],
    [page],
  );

  function navigate(nextPage: AppPage) {
    startTransition(() => {
      setPage(nextPage);
    });
  }

  function handleRefreshHome() {
    void hydrateData();
  }

  if (loading) {
    return (
      <main className="shell-root">
        <div className="shell shell-single">
          <section className="panel center-panel">
            <p className="eyebrow">正在载入</p>
            <h1>先把今天的 Pulse 准备好</h1>
            <p className="hero-summary">
              Frontend-1 默认读取 curated mock JSON，不连接真实平台。
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
              <p>Frontend-1 只预留 API mode，默认仍然必须能在本地 mock mode 运行。</p>
            </StatusBanner>
            <button className="button-primary" onClick={() => void hydrateData()}>
              重试加载 mock 数据
            </button>
          </section>
        </div>
      </main>
    );
  }

  return (
    <main className="shell-root">
      <div className="shell">
        <aside className="sidebar">
          <div className="brand-card">
            <div className="brand-mark">RP</div>
            <div>
              <p className="eyebrow">minimal web shell</p>
              <h2 className="sidebar-title">Research Pulse</h2>
              <p className="soft-copy">Frontend-1 只做三页，不做完整产品后台。</p>
            </div>
          </div>

          <section className="sidebar-card">
            <p className="eyebrow">当前模式</p>
            <div className="badge-row">
              <Badge tone="draft">mock</Badge>
              <Badge tone="not-sent">api 预留</Badge>
            </div>
            <p className="soft-copy">
              real API mode 仅保留后续内部联调入口，本轮默认不启用。
            </p>
          </section>

          <nav className="nav-stack" aria-label="页面导航">
            {navigationItems.map((item) => (
              <button
                key={item.key}
                className={`nav-item ${page === item.key ? "nav-item-active" : ""}`}
                onClick={() => navigate(item.key)}
                type="button"
              >
                <strong>{item.label}</strong>
                <span>{item.description}</span>
              </button>
            ))}
          </nav>

          <section className="sidebar-card">
            <p className="eyebrow">API mode 预留</p>
            <ul className="endpoint-list">
              <li>{apiModePlan.importPreview}</li>
              <li>{apiModePlan.importCommit}</li>
              <li>{apiModePlan.progressSummary}</li>
              <li>{apiModePlan.pulseContext}</li>
              <li>{apiModePlan.dailyPulse}</li>
            </ul>
          </section>
        </aside>

        <div className="content">
          <header className="top-bar">
            <div>
              <p className="eyebrow">当前页面</p>
              <h2>{currentPageMeta.label}</h2>
            </div>
            <div className="top-bar-meta">
              <Badge tone="preview">仅本地演示</Badge>
              <span>最近刷新：{lastRefreshedAt}</span>
            </div>
          </header>

          {page === "home" ? (
            <HomePage
              pulse={shellData.researchPulse}
              summary={shellData.progressSummary}
              channelStates={shellData.channelStates}
              lastRefreshedAt={lastRefreshedAt}
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
              onGenerateOfficialDraft={() => setDraftActionTriggered(true)}
              onBackHome={() => navigate("home")}
            />
          ) : null}
        </div>
      </div>
    </main>
  );
}

export default App;
