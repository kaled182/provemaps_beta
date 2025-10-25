const loadDashboardModule = () => {
  jest.resetModules();
  delete global.google;
  document.body.innerHTML = "";

  global.google = {
    maps: {
      ControlPosition: {
        RIGHT_BOTTOM: "RIGHT_BOTTOM",
        TOP_RIGHT: "TOP_RIGHT",
      },
      event: {
        addListener: jest.fn(),
        removeListener: jest.fn(),
      },
    },
  };

  return require("../dashboard.js");
};

const createControlList = () => {
  const push = jest.fn();
  const controls = {
    RIGHT_BOTTOM: { push: jest.fn() },
    TOP_RIGHT: { push },
  };
  return { controls, push };
};

describe("maps dashboard helpers", () => {
  test("addLegend appends control with legend styling", () => {
    const module = loadDashboardModule();
    const legendControl = { push: jest.fn() };
    module.__setState({
      map: {
        controls: {
          RIGHT_BOTTOM: legendControl,
          TOP_RIGHT: { push: jest.fn() },
        },
      },
    });

    module.addLegend();

    expect(legendControl.push).toHaveBeenCalledTimes(1);
    const element = legendControl.push.mock.calls[0][0];
    expect(element.className).toBe("legend");
    expect(element.innerHTML).toContain("Operational");
  });

  test("addHideMarkersButton toggles marker visibility", () => {
    const module = loadDashboardModule();
    const { controls, push } = createControlList();
    const markers = [
      { setVisible: jest.fn() },
      { setVisible: jest.fn() },
    ];

    module.__setState({
      map: { controls },
      markers,
    });

    module.addHideMarkersButton();

    const button = push.mock.calls[0][0];
    expect(button.textContent).toBe("Hide markers");

    button.click();
    markers.forEach((marker) =>
      expect(marker.setVisible).toHaveBeenLastCalledWith(false)
    );
    expect(button.textContent).toBe("Show markers");

    button.click();
    markers.forEach((marker) =>
      expect(marker.setVisible).toHaveBeenLastCalledWith(true)
    );
    expect(button.textContent).toBe("Hide markers");
  });

  test("addFitBoundsButton triggers map fit via fitMapToBounds handler", () => {
    const module = loadDashboardModule();
    const { controls, push } = createControlList();
    const fitBounds = jest.fn();
    const setZoom = jest.fn();
    const getZoom = jest.fn(() => 10);
    module.__setState({
      map: {
        controls,
        fitBounds,
        setZoom,
        getZoom,
      },
      bounds: {
        isEmpty: () => false,
        getNorthEast: () => ({ lat: () => 0.1, lng: () => 0.1 }),
        getSouthWest: () => ({ lat: () => 0.0, lng: () => 0.0 }),
      },
    });

    module.addFitBoundsButton();

    const button = push.mock.calls[0][0];
    button.click();

    expect(fitBounds).toHaveBeenCalledTimes(1);
  });

  test("fitMapToBounds adjusts zoom when bounds are tight", () => {
    const module = loadDashboardModule();
    let idleHandler;
    global.google.maps.event.addListener.mockImplementation((_map, _evt, cb) => {
      idleHandler = cb;
      return "listener";
    });

    const fitBounds = jest.fn();
    const setZoom = jest.fn();
    const getZoom = jest.fn(() => 17);

    module.__setState({
      map: {
        fitBounds,
        setZoom,
        getZoom,
        controls: {
          RIGHT_BOTTOM: { push: jest.fn() },
          TOP_RIGHT: { push: jest.fn() },
        },
      },
      bounds: {
        isEmpty: () => false,
        getNorthEast: () => ({ lat: () => 0.0, lng: () => 0.0 }),
        getSouthWest: () => ({ lat: () => 0.005, lng: () => 0.005 }),
      },
    });

    module.fitMapToBounds();

    expect(fitBounds).toHaveBeenCalled();
    expect(typeof idleHandler).toBe("function");

    idleHandler(); // simulate idle event
    expect(setZoom).toHaveBeenCalledWith(16);
    expect(global.google.maps.event.removeListener).toHaveBeenCalledWith(
      "listener"
    );
  });
});
