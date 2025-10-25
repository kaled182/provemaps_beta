const loadTrafficChartModule = () => {
  let moduleExports;
  jest.isolateModules(() => {
    // Each isolate gets a fresh singleton instance and hooks.
    moduleExports = require("../traffic_chart.js");
  });
  return moduleExports;
};

describe("TrafficChart front-end helpers", () => {
  beforeEach(() => {
    jest.resetModules();
    localStorage.clear();
    document.body.innerHTML = "";
    if (window.__trafficBtnDelegation) {
      delete window.__trafficBtnDelegation;
    }
  });

  test("configure merges preferences and persists them", () => {
    const { TrafficChartManager } = loadTrafficChartModule();
    const manager = new TrafficChartManager();

    manager.configure({
      theme: { mode: "dark" },
      refresh: { enable: true, intervalMs: 5000 },
    });

    expect(manager.config.theme.mode).toBe("dark");
    expect(manager.config.refresh.enable).toBe(true);
    expect(manager.config.refresh.intervalMs).toBe(5000);

    const stored = JSON.parse(localStorage.getItem("trafficChartPrefs"));
    expect(stored.theme.mode).toBe("dark");
    expect(stored.refresh.enable).toBe(true);
    expect(stored.refresh.intervalMs).toBe(5000);
  });

  test("attachTrafficButtonListeners forwards click metadata", () => {
    const { trafficChartManager } = loadTrafficChartModule();
    trafficChartManager.showPortTrafficChart = jest.fn();

    document.body.innerHTML = `
      <button
        class="traffic-btn"
        data-port-id="42"
        data-port-name="Gi1/0/42"
        data-device-name="Edge-SW"
      ></button>
    `;

    window.attachTrafficButtonListeners();

    document.querySelector(".traffic-btn").click();

    expect(trafficChartManager.showPortTrafficChart).toHaveBeenCalledWith(
      "42",
      "Gi1/0/42",
      "Edge-SW"
    );
  });

  test("attachTrafficButtonListeners is idempotent", () => {
    const { trafficChartManager } = loadTrafficChartModule();
    trafficChartManager.showPortTrafficChart = jest.fn();

    document.body.innerHTML = `
      <button
        class="traffic-btn"
        data-port-id="99"
        data-port-name="Gi1/0/99"
        data-device-name="Core-SW"
      ></button>
    `;

    window.attachTrafficButtonListeners();
    window.attachTrafficButtonListeners(); // should not create duplicate handlers

    document.querySelector(".traffic-btn").click();

    expect(trafficChartManager.showPortTrafficChart).toHaveBeenCalledTimes(1);
  });

  test("setTheme updates global theme and triggers refresh", () => {
    const { TrafficChartManager } = loadTrafficChartModule();
    const manager = new TrafficChartManager();
    manager._refreshAllCharts = jest.fn();

    manager.setTheme("light");

    expect(manager.config.theme.mode).toBe("light");
    expect(manager._refreshAllCharts).toHaveBeenCalled();

    const stored = JSON.parse(localStorage.getItem("trafficChartPrefs"));
    expect(stored.theme.mode).toBe("light");
  });

  test("setTheme on specific instance overrides theme and refreshes it", () => {
    const { TrafficChartManager } = loadTrafficChartModule();
    const manager = new TrafficChartManager();
    const instance = { theme: "auto" };
    manager.instances.set("13", instance);
    manager._refreshInstance = jest.fn();

    manager.setTheme("dark", { instanceId: "13" });

    expect(instance.theme).toBe("dark");
    expect(manager._refreshInstance).toHaveBeenCalledWith("13");
  });

  test("startAutoRefresh enables interval and refreshes charts", () => {
    const { TrafficChartManager } = loadTrafficChartModule();
    const manager = new TrafficChartManager();
    manager._refreshAllCharts = jest.fn();

    manager.startAutoRefresh(7000);

    expect(manager.config.refresh.enable).toBe(true);
    expect(manager.config.refresh.intervalMs).toBe(7000);
    expect(manager._refreshAllCharts).toHaveBeenCalled();
  });

  test("_scheduleInstanceRefresh respects refresh flag", () => {
    jest.useFakeTimers();
    const { TrafficChartManager } = loadTrafficChartModule();
    const manager = new TrafficChartManager();
    manager.config.refresh.enable = false;
    const instance = { refreshTimer: null };

    const loadSpy = jest.spyOn(manager, "_loadChartData").mockImplementation(() => {});
    manager._scheduleInstanceRefresh(instance);

    expect(instance.refreshTimer).toBeNull();
    expect(loadSpy).not.toHaveBeenCalled();
    jest.useRealTimers();
  });

  test("_scheduleInstanceRefresh queues data reload when enabled", () => {
    jest.useFakeTimers();
    const { TrafficChartManager } = loadTrafficChartModule();
    const manager = new TrafficChartManager();
    manager.config.refresh.enable = true;
    manager.config.refresh.intervalMs = 2500;
    const instance = { refreshTimer: null };

    const loadSpy = jest.spyOn(manager, "_loadChartData").mockImplementation(() => {});
    manager._scheduleInstanceRefresh(instance);

    expect(instance.refreshTimer).not.toBeNull();
    jest.advanceTimersByTime(2500);
    expect(loadSpy).toHaveBeenCalledWith(instance);

    jest.useRealTimers();
  });
});
