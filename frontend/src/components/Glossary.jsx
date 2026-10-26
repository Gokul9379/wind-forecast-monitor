export default function Glossary() {
  return (
    <section className="card glossary">
      <h2>How to read this</h2>
      <dl>
        <dt>Target time</dt>
        <dd>The half hour that a forecast is about (Elexon <code>startTime</code>).</dd>
        <dt>Forecast horizon</dt>
        <dd>How long before the target time the forecast was published. A 24 h horizon means “the newest forecast that already existed 24 hours earlier”.</dd>
        <dt>Error</dt>
        <dd>Actual minus forecast. <strong>Negative</strong> = less wind than forecast, so extra power (e.g. thermal) had to be bought. <strong>Positive</strong> = more wind than forecast.</dd>
        <dt>MAE / RMSE</dt>
        <dd>Typical size of the error in MW. RMSE punishes large misses more than MAE does.</dd>
        <dt>Bias</dt>
        <dd>Average error. Close to zero means the forecast is not systematically too high or too low.</dd>
        <dt>Conservative wind</dt>
        <dd>The wind level that was met or exceeded in the chosen share of past cases (e.g. 90%). Planning on this value protects against forecast misses.</dd>
      </dl>
    </section>
  );
}
