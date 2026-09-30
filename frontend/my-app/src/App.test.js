import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App, { isOutsideClick } from "./App";

const STREETS = [
  { name: "HAIGHT ST", citations: 1276 },
  { name: "HAYES ST", citations: 702 },
  { name: "HAYES ST & BAKER ST", citations: 40 },
  { name: "GEARY BLVD", citations: 858 },
];

const RISK = {
  zone_id: 7,
  risk_score: 60.5,
  risk_level: "High",
  risk_color: "#FF0000",
  recommendation: "Avoid parking here",
  matched_address: "1179 HAYES ST",
  is_peak_time: false,
  peak_info: { hour: 12, day: "Thursday" },
  statistics: { total_tickets: 702, tickets_per_day: 8.2, data_period_days: 86 },
  location: { latitude: 37.7761, longitude: -122.4365 },
  timestamp: "2026-09-30T13:00:00",
};

beforeEach(() => {
  global.fetch = jest.fn((url) => {
    if (String(url).includes("/streets")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ streets: STREETS }) });
    }
    if (String(url).includes("/zone-info/")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(RISK) });
    }
    return Promise.resolve({ ok: false, json: () => Promise.resolve({}) });
  });
});

afterEach(() => jest.restoreAllMocks());

/** Open the Risk Check panel and wait for the street list to load. */
const openRiskCheck = async () => {
  userEvent.click(screen.getByText("Risk Check"));
  const input = await screen.findByLabelText(/enter street name/i);
  await waitFor(() =>
    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining("/streets"))
  );
  return input;
};

test("suggests matching streets as the user types", async () => {
  render(<App />);
  const input = await openRiskCheck();

  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();

  userEvent.type(input, "hay");
  const options = within(await screen.findByRole("listbox")).getAllByRole("option");

  expect(options.map((o) => o.textContent)).toEqual([
    expect.stringContaining("HAYES ST"),
    expect.stringContaining("HAYES ST & BAKER ST"),
  ]);
});

test("long suffix forms match the stored abbreviation", async () => {
  render(<App />);
  const input = await openRiskCheck();

  userEvent.type(input, "geary boulevard");
  const options = within(await screen.findByRole("listbox")).getAllByRole("option");

  expect(options).toHaveLength(1);
  expect(options[0]).toHaveTextContent("GEARY BLVD");
});

// Regression: picking a suggestion unmounts it, so the click reached the global
// outside-click handler with a detached target and closed the whole panel.
test("clicking a suggestion runs the check and leaves the panel open", async () => {
  render(<App />);
  const input = await openRiskCheck();

  userEvent.type(input, "hay");
  const listbox = await screen.findByRole("listbox");
  // The typed portion is wrapped in <strong>, so match on the name span rather
  // than a text node, and exactly -- "HAYES ST" is a prefix of another option.
  const hayesSt = within(listbox)
    .getAllByRole("option")
    .find((o) => o.querySelector(".suggestion-name").textContent === "HAYES ST");
  userEvent.click(hayesSt);

  // The result arrives...
  expect(await screen.findByText("1179 HAYES ST")).toBeInTheDocument();

  // ...and the panel is still open, with the picked street in the field.
  expect(screen.getByLabelText(/enter street name/i)).toHaveValue("HAYES ST");
  expect(screen.getByRole("heading", { name: "Risk Check" })).toBeInTheDocument();
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
});

test("arrow keys and Enter pick a suggestion", async () => {
  render(<App />);
  const input = await openRiskCheck();

  userEvent.type(input, "hay");
  await screen.findByRole("listbox");

  userEvent.type(input, "{arrowdown}{arrowdown}{enter}");

  expect(await screen.findByText("1179 HAYES ST")).toBeInTheDocument();
  expect(screen.getByLabelText(/enter street name/i)).toHaveValue("HAYES ST & BAKER ST");
});

test("Escape dismisses the dropdown but keeps the panel", async () => {
  render(<App />);
  const input = await openRiskCheck();

  userEvent.type(input, "hay");
  await screen.findByRole("listbox");

  userEvent.type(input, "{esc}");

  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  expect(screen.getByLabelText(/enter street name/i)).toBeInTheDocument();
});

// The detached-target guard must not stop genuine outside clicks from closing.
test("clicking outside still closes the panel", async () => {
  render(<App />);
  await openRiskCheck();

  userEvent.click(document.body);

  await waitFor(() =>
    expect(screen.queryByLabelText(/enter street name/i)).not.toBeInTheDocument()
  );
});

describe("isOutsideClick", () => {
  afterEach(() => { document.body.innerHTML = ""; });

  const buildModal = () => {
    document.body.innerHTML = `
      <div class="tab">Risk Check</div>
      <div class="modal-overlay"></div>
      <div class="info-modal">
        <div class="risk-autocomplete">
          <input id="risk-address" />
          <ul class="risk-suggestions" role="listbox">
            <li role="option"><span class="suggestion-name">HAYES ST</span></li>
          </ul>
        </div>
      </div>`;
    return {
      list: document.querySelector(".risk-suggestions"),
      option: document.querySelector(".suggestion-name"),
    };
  };

  test("a click inside the panel is not outside", () => {
    const { option } = buildModal();
    expect(isOutsideClick(option)).toBe(false);
    expect(isOutsideClick(document.querySelector("#risk-address"))).toBe(false);
    expect(isOutsideClick(document.querySelector(".tab"))).toBe(false);
  });

  test("a click on the overlay or body is outside", () => {
    buildModal();
    expect(isOutsideClick(document.querySelector(".modal-overlay"))).toBe(true);
    expect(isOutsideClick(document.body)).toBe(true);
  });

  // The reported bug: React 18 flushes synchronously during a discrete event, so
  // the suggestion is gone from the document by the time the click reaches window.
  test("a target unmounted mid-dispatch is not treated as outside", () => {
    const { list, option } = buildModal();
    const verdicts = [];

    // Stand in for React's synchronous unmount of the dropdown on selection.
    option.addEventListener("click", () => list.remove());
    window.addEventListener("click", (e) => verdicts.push(isOutsideClick(e.target)), { once: true });

    option.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    expect(option.isConnected).toBe(false); // the mechanism really occurred
    expect(verdicts).toEqual([false]);      // ...and it is not read as an outside click
  });
});
