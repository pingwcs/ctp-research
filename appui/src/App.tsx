import { useEffect, useState, type FormEvent } from 'react';
import { AlertCircle, RefreshCw, Search } from 'lucide-react';

import KLineChart from './components/KLineChart';
import { fetchKLineData, setSymbol } from './store/marketSlice';
import { useAppDispatch, useAppSelector } from './store';

export default function App() {
  const dispatch = useAppDispatch();
  const { symbol, candles, markers, loading, error, lastLoadedAt } = useAppSelector(
    (state) => state.market,
  );
  const [draftSymbol, setDraftSymbol] = useState(symbol);

  useEffect(() => {
    void dispatch(fetchKLineData(symbol));
  }, [dispatch]);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextSymbol = draftSymbol.trim().toUpperCase();
    if (!nextSymbol) return;
    dispatch(setSymbol(nextSymbol));
    void dispatch(fetchKLineData(nextSymbol));
  };

  const refresh = () => {
    void dispatch(fetchKLineData(symbol));
  };

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <section className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-4 sm:px-6">
        <header className="flex flex-col gap-3 border-b border-zinc-800 pb-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-normal text-white">Futures K-Line</h1>
            <p className="mt-1 text-sm text-zinc-400">
              {candles.length ? `${symbol} · ${candles.length.toLocaleString()} bars` : symbol}
            </p>
          </div>

          <form className="flex w-full gap-2 md:w-auto" onSubmit={submit}>
            <label className="sr-only" htmlFor="symbol">
              Symbol
            </label>
            <input
              id="symbol"
              className="h-10 min-w-0 flex-1 rounded border border-zinc-700 bg-zinc-900 px-3 font-mono text-sm text-zinc-100 outline-none transition focus:border-cyan-500 md:w-44"
              value={draftSymbol}
              onChange={(event) => setDraftSymbol(event.target.value)}
              placeholder="RB0909"
              spellCheck={false}
            />
            <button
              className="inline-flex h-10 w-10 items-center justify-center rounded border border-cyan-600 bg-cyan-600 text-white transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-60"
              type="submit"
              disabled={loading}
              title="Search"
            >
              <Search size={18} />
            </button>
            <button
              className="inline-flex h-10 w-10 items-center justify-center rounded border border-zinc-700 bg-zinc-900 text-zinc-200 transition hover:border-zinc-500 disabled:cursor-not-allowed disabled:opacity-60"
              type="button"
              onClick={refresh}
              disabled={loading}
              title="Refresh"
            >
              <RefreshCw className={loading ? 'animate-spin' : ''} size={18} />
            </button>
          </form>
        </header>

        {error ? (
          <div className="mt-4 flex items-start gap-2 rounded border border-red-500/50 bg-red-950/40 px-3 py-2 text-sm text-red-100">
            <AlertCircle className="mt-0.5 shrink-0" size={16} />
            <span>{error}</span>
          </div>
        ) : null}

        <section className="mt-4 min-h-0 flex-1">
          <KLineChart candles={candles} markers={markers} loading={loading} symbol={symbol} />
        </section>

        <footer className="flex min-h-10 items-center justify-between border-t border-zinc-800 pt-3 text-xs text-zinc-500">
          <span>Data API: /api/market/kline</span>
          <span>{lastLoadedAt ? new Date(lastLoadedAt).toLocaleString() : ''}</span>
        </footer>
      </section>
    </main>
  );
}
