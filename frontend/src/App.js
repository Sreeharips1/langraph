import React from "react";
import { Provider } from "react-redux";
import { store } from "./redux/store";
import LogInteraction from "./pages/LogInteraction";

const App = () => {
  return (
    <Provider store={store}>
      <LogInteraction />
    </Provider>
  );
};

export default App;
