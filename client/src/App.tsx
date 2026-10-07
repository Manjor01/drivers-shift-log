import { useEffect, useState } from "react";
import "./style.css";

type Totals = {
  trip_count: number;
  revenue: number;
  commission: number;
  net: number;
};
type Trip = {
  id: string;
  start: string;
  end: string;
  amount: number;
  payment: "cash" | "card";
  commission: number;
};
type Day = {
  day: string;
  timezone: string;
  summary: { total: Totals; cash: Totals; card: Totals };
  trips: Trip[];
};
const money = (value: number) =>
  `${new Intl.NumberFormat("ru-KZ").format(value)} ₸`;

export default function App() {
  const [day, setDay] = useState("2026-10-01");
  const [data, setData] = useState<Day | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/day?day=${encodeURIComponent(day)}`, {
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("Не удалось загрузить поездки");
        return (await response.json()) as Day;
      })
      .then(setData)
      .catch((err: unknown) => {
        if (!controller.signal.aborted)
          setError(err instanceof Error ? err.message : "Ошибка сети");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [day, version]);

  const reset = () => {
    setLoading(true);
    setError("");
    setData(null);
  };
  const chooseDay = (value: string) => {
    reset();
    setDay(value);
  };
  const reload = () => {
    reset();
    setVersion((value) => value + 1);
  };
  const shift = (amount: number) => {
    const date = new Date(`${day}T12:00:00Z`);
    date.setUTCDate(date.getUTCDate() + amount);
    chooseDay(date.toISOString().slice(0, 10));
  };
  const time = (value: string) =>
    new Intl.DateTimeFormat("ru-KZ", {
      timeZone: data?.timezone ?? "Asia/Almaty",
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "2-digit",
    }).format(new Date(value));

  async function addTrip(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const fields = new FormData(form);
    setSaving(true);
    setNotice("");
    try {
      const response = await fetch("/api/trips", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: fields.get("id"),
          start: fields.get("start"),
          end: fields.get("end"),
          amount: Number(fields.get("amount")),
          commission: Number(fields.get("commission")),
          payment: fields.get("payment"),
        }),
      });
      if (!response.ok) {
        if (response.status === 409)
          throw new Error("Этот ID уже принадлежит поездке с другими данными.");
        if (response.status === 422)
          throw new Error(
            "Проверьте ID, суммы и время. Нужен часовой пояс; окончание позже начала.",
          );
        throw new Error("Не удалось сохранить поездку.");
      }
      setNotice(
        response.status === 201
          ? "Поездка добавлена."
          : "Поездка уже сохранена — дубль не создан.",
      );
      reload();
    } catch (err: unknown) {
      setNotice(err instanceof Error ? err.message : "Ошибка сети");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main>
      <header>
        <div className="brand">SHIFT / ДНЕВНИК ВОДИТЕЛЯ</div>
        <span className="badge">{data?.timezone ?? "Asia/Almaty"} · KZT</span>
      </header>
      <section className="intro">
        <p className="eyebrow">КАЖДАЯ ПОЕЗДКА НА СВОЁМ МЕСТЕ</p>
        <h1>Дневник смен</h1>
        <p className="sub">Поездки и доход за выбранный день</p>
      </section>
      <section className="daybar" aria-label="Выбор дня">
        <button aria-label="Предыдущий день" onClick={() => shift(-1)}>
          ←
        </button>
        <label>
          День смены{" "}
          <input
            aria-label="День смены"
            type="date"
            value={day}
            onChange={(e) => {
              if (e.target.value) chooseDay(e.target.value);
            }}
          />
        </label>
        <button aria-label="Следующий день" onClick={() => shift(1)}>
          →
        </button>
      </section>
      {loading && <p role="status">Загрузка смены…</p>}
      {error && (
        <div role="alert" className="error">
          {error} <button onClick={reload}>Повторить</button>
        </div>
      )}
      {data && (
        <>
          <section className="metrics" aria-label="Сводка за день">
            {[
              ["Поездки", String(data.summary.total.trip_count)],
              ["Выручка", money(data.summary.total.revenue)],
              ["Комиссия", money(data.summary.total.commission)],
              ["На руки", money(data.summary.total.net)],
            ].map(([name, value]) => (
              <article
                className={name === "На руки" ? "metric accent" : "metric"}
                key={name}
              >
                <span>{name}</span>
                <strong>{value}</strong>
              </article>
            ))}
          </section>
          <section className="payments">
            {(["cash", "card"] as const).map((method) => (
              <article key={method}>
                <h2>{method === "cash" ? "Наличные" : "Карта"}</h2>
                <strong>{money(data.summary[method].revenue)}</strong>
                <p>
                  {data.summary[method].trip_count} поездок · комиссия{" "}
                  {money(data.summary[method].commission)}
                </p>
                <p>На руки: {money(data.summary[method].net)}</p>
              </article>
            ))}
          </section>
          <section className="panel">
            <div className="panel-title">
              <h2>Поездки</h2>
              <span>{data.trips.length} за день</span>
            </div>
            {data.trips.length === 0 ? (
              <p className="empty">
                За этот день поездок пока нет. Выберите другой день или добавьте
                поездку.
              </p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Начало</th>
                      <th>Окончание</th>
                      <th>Оплата</th>
                      <th>Сумма</th>
                      <th>Комиссия</th>
                      <th>На руки</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.trips.map((trip) => (
                      <tr key={trip.id}>
                        <td>{trip.id}</td>
                        <td>{time(trip.start)}</td>
                        <td>{time(trip.end)}</td>
                        <td>
                          <span className="pill">
                            {trip.payment === "cash" ? "Наличные" : "Карта"}
                          </span>
                        </td>
                        <td>{money(trip.amount)}</td>
                        <td>{money(trip.commission)}</td>
                        <td className="net">
                          {money(trip.amount - trip.commission)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
      <details className="panel">
        <summary>Добавить поездку</summary>
        <form onSubmit={addTrip}>
          <label>
            ID
            <input
              name="id"
              required
              maxLength={64}
              pattern="[A-Za-z0-9._:\-]{1,64}"
              placeholder="trip-003"
            />
          </label>
          <label>
            Начало (ISO 8601)
            <input
              name="start"
              required
              placeholder={`${day}T10:00:00+05:00`}
            />
          </label>
          <label>
            Окончание (ISO 8601)
            <input name="end" required placeholder={`${day}T10:25:00+05:00`} />
          </label>
          <label>
            Сумма, ₸
            <input
              name="amount"
              type="number"
              required
              min={1}
              max={1000000000}
              step={1}
            />
          </label>
          <label>
            Комиссия, ₸
            <input name="commission" type="number" required min={0} step={1} />
          </label>
          <label>
            Оплата
            <select name="payment">
              <option value="card">Карта</option>
              <option value="cash">Наличные</option>
            </select>
          </label>
          <button className="primary" disabled={saving}>
            {saving ? "Сохраняем…" : "Сохранить поездку"}
          </button>
          <p role="status">{notice}</p>
        </form>
      </details>
      <footer>
        День определяется по началу поездки. На руки = выручка − комиссия.
      </footer>
    </main>
  );
}
