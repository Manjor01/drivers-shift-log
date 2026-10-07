import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import App from "./App";
const totals = { trip_count: 2, revenue: 3900, commission: 585, net: 3315 };
const body = {
  day: "2026-10-01",
  timezone: "Asia/Almaty",
  summary: {
    total: totals,
    cash: { trip_count: 1, revenue: 1500, commission: 225, net: 1275 },
    card: { trip_count: 1, revenue: 2400, commission: 360, net: 2040 },
  },
  trips: [
    {
      id: "t1",
      start: "2026-10-01T08:10:00+05:00",
      end: "2026-10-01T08:32:00+05:00",
      amount: 2400,
      commission: 360,
      payment: "card",
    },
  ],
};
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
test("loads summary and switches days", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => body });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  expect(await screen.findByText("t1")).toBeInTheDocument();
  expect(screen.getByText(/3\s?315 ₸/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Следующий день" }));
  await waitFor(() =>
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/day?day=2026-10-02",
      expect.anything(),
    ),
  );
});
test("shows empty state", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ...body, trips: [] }),
    }),
  );
  render(<App />);
  expect(
    await screen.findByText(/За этот день поездок пока нет/),
  ).toBeInTheDocument();
});
test("shows a network failure with retry", async () => {
  const fetchMock = vi.fn().mockRejectedValue(new Error("Ошибка сети"));
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Ошибка сети");
  fireEvent.click(screen.getByRole("button", { name: "Повторить" }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
});

test("posts a trip with integer amounts and displays safe retry result", async () => {
  const fetchMock = vi
    .fn()
    .mockImplementation(async (_url: string, options?: RequestInit) =>
      options?.method === "POST"
        ? { ok: true, status: 200 }
        : { ok: true, json: async () => body },
    );
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await screen.findByText("t1");
  fireEvent.change(screen.getByLabelText("ID"), {
    target: { value: "trip-003" },
  });
  fireEvent.change(screen.getByLabelText("Начало (ISO 8601)"), {
    target: { value: "2026-10-01T10:00:00+05:00" },
  });
  fireEvent.change(screen.getByLabelText("Окончание (ISO 8601)"), {
    target: { value: "2026-10-01T10:25:00+05:00" },
  });
  fireEvent.change(screen.getByLabelText("Сумма, ₸"), {
    target: { value: "1000" },
  });
  fireEvent.change(screen.getByLabelText("Комиссия, ₸"), {
    target: { value: "150" },
  });
  fireEvent.submit(
    screen.getByRole("button", { name: "Сохранить поездку" }).closest("form")!,
  );
  expect(
    await screen.findByText("Поездка уже сохранена — дубль не создан."),
  ).toBeInTheDocument();
  const call = fetchMock.mock.calls.find(
    ([, options]) => options?.method === "POST",
  );
  expect(JSON.parse(call?.[1]?.body as string)).toEqual({
    id: "trip-003",
    start: "2026-10-01T10:00:00+05:00",
    end: "2026-10-01T10:25:00+05:00",
    amount: 1000,
    commission: 150,
    payment: "card",
  });
});
