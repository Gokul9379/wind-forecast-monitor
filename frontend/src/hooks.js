import { useEffect, useState } from "react";

/**
 * Run an async loader whenever `deps` change and expose {data, loading, error}.
 * The previous request is cancelled so a slow, old response can never overwrite a newer one.
 */
export function useApi(loader, deps) {
  const [state, setState] = useState({ data: null, loading: true, error: null });

  useEffect(() => {
    const controller = new AbortController();
    setState((previous) => ({ ...previous, loading: true, error: null }));
    loader(controller.signal)
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((error) => {
        if (error.name !== "AbortError") setState({ data: null, loading: false, error: error.message });
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}

/** Return `value`, but only after it has stopped changing for `delay` ms (used for the slider). */
export function useDebounced(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
