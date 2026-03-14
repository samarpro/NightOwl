import type { TokenEntry } from "entities/token/model/types";

type TokenViewerProps = {
  tokens: TokenEntry[];
};

export function TokenViewer({ tokens }: TokenViewerProps) {
  return (
    <div className="token-list">
      {tokens.map((token) => (
        <article className="token-card" key={token.id}>
          <header>
            <div className="token-type">{token.type}</div>
            <span className="muted">{new Date(token.createdAt).toLocaleTimeString()}</span>
          </header>
          <pre>{token.content}</pre>
        </article>
      ))}
    </div>
  );
}
