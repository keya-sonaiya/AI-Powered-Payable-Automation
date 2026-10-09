import type { ReactNode } from "react";

const TOKEN_PATTERN = /(\*\*[^*]+\*\*|`[^`]+`)/g;

export function stripInlineMarkdown(text: string): string {
  return text.replace(/\*\*([^*]+)\*\*|`([^`]+)`/g, "$1$2");
}

export default function InlineMarkdown({ text }: { text: string }): ReactNode {
  const parts: ReactNode[] = [];
  let lastIndex = 0;

  for (const match of text.matchAll(TOKEN_PATTERN)) {
    const index = match.index ?? 0;
    if (index > lastIndex) {
      parts.push(text.slice(lastIndex, index));
    }

    const token = match[0];
    if (token.startsWith("**")) {
      parts.push(<strong key={index}>{token.slice(2, -2)}</strong>);
    } else {
      parts.push(<code key={index}>{token.slice(1, -1)}</code>);
    }
    lastIndex = index + token.length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}
