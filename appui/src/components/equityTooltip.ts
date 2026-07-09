interface EquityPointPosition {
  x: number;
  y: number;
}

interface EquityChartBounds {
  width: number;
  height: number;
}

interface EquityTooltipPlacement {
  left: string;
  top: string;
  transform: string;
}

const TOOLTIP_OFFSET = 14;
const EDGE_THRESHOLD = 0.66;
const LOW_EDGE_THRESHOLD = 0.55;

function formatPercent(value: number) {
  return `${Number(value.toFixed(4))}%`;
}

export function getEquityTooltipPlacement(
  point: EquityPointPosition,
  bounds: EquityChartBounds,
): EquityTooltipPlacement {
  const left = formatPercent((point.x / bounds.width) * 100);
  const top = formatPercent((point.y / bounds.height) * 100);
  const translateX =
    point.x / bounds.width > EDGE_THRESHOLD
      ? `calc(-100% - ${TOOLTIP_OFFSET}px)`
      : `${TOOLTIP_OFFSET}px`;
  const translateY =
    point.y / bounds.height > LOW_EDGE_THRESHOLD
      ? `calc(-100% - ${TOOLTIP_OFFSET}px)`
      : `${TOOLTIP_OFFSET}px`;

  return {
    left,
    top,
    transform: `translate(${translateX}, ${translateY})`,
  };
}
