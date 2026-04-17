import {
  isSafeExternalHref,
  stableSectionOrder,
} from "../lib/shareModel";
import type { DigestShareViewModel, SharedDigestItemRead } from "../lib/types";

type DigestShareViewProps = {
  viewModel: DigestShareViewModel;
};

function DigestItemCard({ item }: { item: SharedDigestItemRead }) {
  const deepLinkExternal = isSafeExternalHref(item.deep_link);

  return (
    <article className="list-card">
      <div className="list-card-header">
        <div>
          <h4>{item.title}</h4>
          <p className="meta-copy">
            {item.card_type}
            {item.source_paper_id ? ` · paper ${item.source_paper_id}` : " · no paper link"}
          </p>
        </div>
        <span className="pill">#{item.sort_order}</span>
      </div>
      <p>{item.summary}</p>
      {item.why_now ? <p className="soft-copy">Why now: {item.why_now}</p> : null}
      {item.action_text ? <p className="soft-copy">Action: {item.action_text}</p> : null}
      {item.paper ? (
        <p className="soft-copy">
          Paper: {item.paper.title} · {item.paper.stage} · {item.paper.progress_percentage}%
        </p>
      ) : null}
      {item.deep_link ? (
        deepLinkExternal ? (
          <a href={item.deep_link} rel="noreferrer noopener" target="_blank">
            Open safe external link
          </a>
        ) : (
          <p className="soft-copy">
            Internal link hint: <code>{item.deep_link}</code>
          </p>
        )
      ) : null}
    </article>
  );
}

export function DigestShareView({ viewModel }: DigestShareViewProps) {
  const sectionOrderCopy = stableSectionOrder.join(" -> ");
  const articleUrlSafe = isSafeExternalHref(viewModel.publicationPreview?.article_url ?? null);

  return (
    <div className="page-stack">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Digest Issue Share</p>
          <h2>{viewModel.pageTitle}</h2>
          <p className="lede">{viewModel.pageSubtitle}</p>
        </div>
        <div className="hero-actions">
          <div className="hero-chip">
            <span>Issue date</span>
            <strong>{viewModel.issueDate}</strong>
          </div>
          <div className="hero-chip">
            <span>Fallback mode</span>
            <strong>{viewModel.fallbackMode}</strong>
          </div>
        </div>
      </section>

      <section className="summary-grid">
        <article className="summary-card">
          <p className="eyebrow">Counts</p>
          <dl className="summary-list">
            <div>
              <dt>Highlights</dt>
              <dd>{viewModel.highlightCount}</dd>
            </div>
            <div>
              <dt>Selected cards</dt>
              <dd>{viewModel.selectedCardCount}</dd>
            </div>
          </dl>
        </article>
        <article className="summary-card">
          <p className="eyebrow">Structured mode</p>
          <p>{viewModel.isStructured ? "Structured digest available" : "Legacy fallback view"}</p>
          <p className="soft-copy">Stable section order: {sectionOrderCopy}</p>
        </article>
        {viewModel.quickStats ? (
          <article className="summary-card">
            <p className="eyebrow">Quick stats</p>
            <dl className="summary-list">
              <div>
                <dt>Touched papers</dt>
                <dd>{viewModel.quickStats.touched_paper_count}</dd>
              </div>
              <div>
                <dt>Signal updates</dt>
                <dd>{viewModel.quickStats.signal_update_count}</dd>
              </div>
              <div>
                <dt>Related papers</dt>
                <dd>{viewModel.quickStats.related_paper_count}</dd>
              </div>
            </dl>
          </article>
        ) : null}
      </section>

      {viewModel.focusCard ? (
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Focus Card</p>
              <h3>{viewModel.focusCard.title}</h3>
            </div>
          </div>
          <DigestItemCard item={viewModel.focusCard} />
        </section>
      ) : null}

      {viewModel.publicationPreview ? (
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Publication Preview</p>
              <h3>{viewModel.publicationPreview.digest_title ?? viewModel.pageTitle}</h3>
            </div>
          </div>
          {viewModel.publicationPreview.digest_subtitle ? (
            <p>{viewModel.publicationPreview.digest_subtitle}</p>
          ) : null}
          <dl className="summary-list compact">
            <div>
              <dt>Primary CTA</dt>
              <dd>{viewModel.publicationPreview.primary_cta_text ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Primary path</dt>
              <dd>
                {viewModel.publicationPreview.primary_cta_path ? (
                  <code>{viewModel.publicationPreview.primary_cta_path}</code>
                ) : (
                  "Unavailable"
                )}
              </dd>
            </div>
            <div>
              <dt>Mini path</dt>
              <dd>
                {viewModel.publicationPreview.mini_program_path ? (
                  <code>{viewModel.publicationPreview.mini_program_path}</code>
                ) : (
                  "Unavailable"
                )}
              </dd>
            </div>
            <div>
              <dt>Article URL</dt>
              <dd>
                {articleUrlSafe ? (
                  <a
                    href={viewModel.publicationPreview.article_url ?? undefined}
                    rel="noreferrer noopener"
                    target="_blank"
                  >
                    Open external article
                  </a>
                ) : (
                  "Unavailable"
                )}
              </dd>
            </div>
          </dl>
        </section>
      ) : null}

      <section className="page-stack">
        {viewModel.sectionViews.map((section) => (
          <section className="panel-card" key={section.kind}>
            <div className="section-heading">
              <div>
                <p className="eyebrow">{section.kind}</p>
                <h3>{section.title}</h3>
              </div>
              <span className="pill">{section.item_count} item(s)</span>
            </div>
            <div className="list-stack">
              {section.items.map((item) => (
                <DigestItemCard item={item} key={item.pulse_card_id} />
              ))}
            </div>
          </section>
        ))}
      </section>

      {!viewModel.isStructured && viewModel.legacyHighlights.length > 0 ? (
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Legacy Compatibility</p>
              <h3>Original highlight payload</h3>
            </div>
          </div>
          <p className="soft-copy">
            This share was rendered from fallback highlight/item data because no full structured
            section payload was available.
          </p>
        </section>
      ) : null}
    </div>
  );
}
