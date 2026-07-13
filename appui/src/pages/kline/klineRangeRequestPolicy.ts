export type RangeRequestDecision = 'dispatch' | 'queue' | 'skip';

interface RangeRequestPolicyInput {
  activeRequestKey: string | null;
  lastRequestedRange: string | null;
  rangeKey: string;
  requestKey: string;
  total: number;
}

export function getRangeRequestDecision({
  activeRequestKey,
  lastRequestedRange,
  rangeKey,
  requestKey,
  total,
}: RangeRequestPolicyInput): RangeRequestDecision {
  if (!total) return 'skip';
  if (lastRequestedRange === rangeKey) return 'skip';
  if (activeRequestKey === requestKey) return 'skip';

  return activeRequestKey ? 'queue' : 'dispatch';
}
