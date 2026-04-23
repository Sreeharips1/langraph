import FormSection from "../components/FormSection";
import ChatSection from "../components/ChatSection";

export default function LogInteraction() {
  return (
    <div className="container">
      <div style={{ flex: 2 }}>
        <FormSection />
      </div>
      <div style={{ flex: 1 }}>
        <ChatSection />
      </div>
    </div>
  );
}
