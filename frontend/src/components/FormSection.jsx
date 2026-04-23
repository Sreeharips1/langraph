import { useSelector } from "react-redux";

export default function FormSection() {
  const form = useSelector((state) => state.form);

  return (
    <div className="card">
      <div className="title">HCP Interaction</div>

      {/* 🔹 Interaction Details */}
      <div className="section">
        <div className="section-title">Interaction Details</div>

        <div className="row">
          <input
            className="input"
            placeholder="HCP Name"
            value={form.hcp_name || ""}
            readOnly
          />
          <input className="input" value="Meeting" readOnly />
        </div>

        <div className="row">
          <input
            className="input"
            placeholder="Date"
            value={form.date || ""}
            readOnly
          />
          <input
            className="input"
            placeholder="Time"
            value={form.time || ""}
            readOnly
          />
        </div>

        <input
          className="input"
          placeholder="Attendees"
          value={(form.attendees || []).join(", ")}
          readOnly
        />
      </div>

      {/* 🔹 Discussion */}
      <div className="section">
        <div className="section-title">Discussion</div>

        <textarea
          className="textarea"
          placeholder="Topics Discussed"
          value={form.topics || ""}
          readOnly
        />

        <textarea
          className="textarea"
          placeholder="Outcomes"
          value={form.outcomes || ""}
          readOnly
        />
      </div>

      {/* 🔹 AI Insights (🔥 MAIN FEATURE) */}
      <div className="section highlight">
        <div className="section-title">AI Insights</div>

        <div className="row">
          <input
            className="input"
            placeholder="Sentiment"
            value={form.sentiment || ""}
            readOnly
          />
        </div>

        <textarea
          className="textarea"
          placeholder="Follow-up Actions"
          value={form.follow_up || ""}
          readOnly
        />

        <textarea
          className="textarea"
          placeholder="Summary"
          value={form.summary || ""}
          readOnly
        />
      </div>

      {/* 🔹 Resources */}
      <div className="section">
        <div className="section-title">Resources Shared</div>

        <input
          className="input"
          placeholder="Materials Shared"
          value={(form.materials_shared || []).join(", ")}
          readOnly
        />

        <input
          className="input"
          placeholder="Samples Distributed"
          value={(form.samples || []).join(", ")}
          readOnly
        />
      </div>
    </div>
  );
}
