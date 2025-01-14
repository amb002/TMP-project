import React, { useState } from "react";
import axios from "axios";

const MatchFingerprint = () => {
  const [message, setMessage] = useState("");
  const [matchedId, setMatchedId] = useState(null);
  const [alias, setAlias] = useState("");
  const [confidence, setConfidence] = useState(null);
  const [error, setError] = useState("");

  const handleMatchFingerprint = async () => {
    setMessage("");
    setMatchedId(null);
    setAlias("");
    setConfidence(null);
    setError("");

    try {
      const response = await axios.post("http://localhost:8000/match");
      const data = response.data;
      setMessage(data.message);
      setMatchedId(data.id);
      setAlias(data.alias);
      setConfidence(data.confidence);
    } catch (err) {
      if (err.response) {
        setError(err.response.data.detail || "Failed to match fingerprint.");
      } else {
        setError("An error occurred. Please try again.");
      }
    }
  };

  return (
    <div style={{ textAlign: "center", marginTop: "50px" }}>
      <h1>Match Fingerprint</h1>
      <button
        onClick={handleMatchFingerprint}
        style={{
          padding: "10px 20px",
          fontSize: "16px",
          cursor: "pointer",
          backgroundColor: "#007BFF",
          color: "#FFF",
          border: "none",
          borderRadius: "5px",
        }}
      >
        Match Fingerprint
      </button>
      {message && (
        <div style={{ marginTop: "20px", color: "green" }}>
          <h3>{message}</h3>
          <p>ID: {matchedId}</p>
          <p>Alias: {alias}</p>
          <p>Confidence: {confidence}</p>
        </div>
      )}
      {error && (
        <div style={{ marginTop: "20px", color: "red" }}>
          <h3>Error</h3>
          <p>{error}</p>
        </div>
      )}
    </div>
  );
};

export default MatchFingerprint;
