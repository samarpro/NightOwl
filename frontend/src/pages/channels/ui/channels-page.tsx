import { useState } from "react";
import { buildChannels } from "entities/channel/model/selectors";
import type { ChannelItem } from "entities/channel/model/types";
import { useDashboardData } from "features/dashboard/model/use-dashboard-data";

export function ChannelsPage() {
  const { data, isLoading } = useDashboardData();

  if (isLoading || !data) {
    return <div className="app-shell">Loading channels…</div>;
  }

  const channels = buildChannels(data.sessions);
  const [selectedChannelId, setSelectedChannelId] = useState(channels[0]?.id ?? null);
  const selectedChannel = channels.find((channel) => channel.id === selectedChannelId) ?? channels[0];

  return (
    <div className="app-shell">
      <div className="app-frame">
        <header className="topbar">
          <div className="topbar__title">
            <span className="eyebrow">NightOwl Channels</span>
            <h1>Observe health, routing, and pairing posture for every channel.</h1>
            <p>
              Sessions stay in the Sessions workspace. Channels now get their own control surface
              with a left rail and detailed status groups on the right.
            </p>
          </div>
          <div className="status-row">
            <span className="pill">{channels.filter((channel) => channel.connected).length} connected</span>
            <span className="pill">{channels.filter((channel) => channel.traffic === "active").length} active</span>
            <span className="pill">{channels.length} supported</span>
          </div>
        </header>

        <div className="channels-layout">
          <aside className="channel-sidebar">
            <div className="panel__header">
              <div>
                <h2>Channels</h2>
                <p>Vertical navigation for channel-specific diagnostics.</p>
              </div>
            </div>
            <div className="channel-sidebar__body">
              {channels.map((channel) => (
                <button
                  className="channel-nav-item"
                  data-selected={selectedChannel?.id === channel.id}
                  key={channel.id}
                  onClick={() => setSelectedChannelId(channel.id)}
                  type="button"
                >
                  <span className="channel-nav-item__icon">{channel.icon}</span>
                  <span className="channel-nav-item__text">
                    <strong>{channel.name}</strong>
                    <span>{channel.health}</span>
                  </span>
                </button>
              ))}
            </div>
          </aside>

          <section className="panel">
            <div className="panel__header">
              <div>
                <h2>Channel Control Center</h2>
                <p>Grouped by Active channels, Unactive, and Supported channels with per-channel detail.</p>
              </div>
            </div>
            <div className="panel__body channels-content">
              <ChannelSection
                items={channels.filter((channel) => channel.traffic === "active")}
                selectedChannelId={selectedChannel?.id ?? null}
                title="Active channels"
              />
              <ChannelSection
                items={channels.filter((channel) => channel.traffic === "idle" && channel.configured)}
                selectedChannelId={selectedChannel?.id ?? null}
                title="Unactive"
              />
              <ChannelSection
                items={channels.filter((channel) => !channel.configured)}
                selectedChannelId={selectedChannel?.id ?? null}
                title="Supported channels"
              />

              {selectedChannel ? (
                <article className="channel-detail-card">
                  <div className="detail-row">
                    <strong>{selectedChannel.name}</strong>
                    <span className={`badge badge--channel badge--${selectedChannel.health}`}>
                      {selectedChannel.health}
                    </span>
                  </div>
                  <p className="approval-card__justification">{selectedChannel.detail}</p>
                  <div className="channel-detail-grid">
                    <DetailStat label="Configured" value={selectedChannel.configured ? "yes" : "no"} />
                    <DetailStat label="Connected" value={selectedChannel.connected ? "yes" : "no"} />
                    <DetailStat label="Traffic" value={selectedChannel.traffic} />
                    <DetailStat label="Auth" value={selectedChannel.authState} />
                    <DetailStat label="Pairing" value={selectedChannel.pairing} />
                    <DetailStat label="Allowlist" value={selectedChannel.allowlist} />
                    <DetailStat label="Typing" value={selectedChannel.typing ? "supported" : "off"} />
                    <DetailStat
                      label="Last inbound"
                      value={selectedChannel.lastInbound ? new Date(selectedChannel.lastInbound).toLocaleTimeString() : "none"}
                    />
                  </div>
                  <div className="channel-routes">
                    <span className="small-label">Linked routes</span>
                    {selectedChannel.linkedRoutes.length > 0 ? (
                      selectedChannel.linkedRoutes.map((route) => (
                        <span className="channel-route-pill" key={route}>
                          {route}
                        </span>
                      ))
                    ) : (
                      <span className="muted">No active routes yet.</span>
                    )}
                  </div>
                </article>
              ) : null}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function ChannelSection({
  title,
  items,
  selectedChannelId
}: {
  title: string;
  items: ChannelItem[];
  selectedChannelId: string | null;
}) {
  return (
    <section className="channel-section">
      <div className="channel-section__header">
        <h3>{title}</h3>
        <span className="muted">{items.length} channels</span>
      </div>
      <div className="channel-card-grid">
        {items.map((channel) => (
          <article className="channel-card" data-selected={channel.id === selectedChannelId} key={channel.id}>
            <div className="detail-row">
              <strong>{channel.name}</strong>
              <span className={`badge badge--channel badge--${channel.health}`}>{channel.health}</span>
            </div>
            <p>{channel.detail}</p>
            <div className="detail-row">
              <span className="muted">{channel.authState}</span>
              <span className="muted">{channel.traffic}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function DetailStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
