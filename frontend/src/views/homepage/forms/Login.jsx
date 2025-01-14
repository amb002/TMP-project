import React, { useState } from "react";
import axios from "axios";

const MatchFingerprint = () => {
  const match_url = "http://localhost:8000/match";
  const [message, setMessage] = useState("");
  const [matchedId, setMatchedId] = useState(null);
  const [alias, setAlias] = useState("");
  const [confidence, setConfidence] = useState(null);
  const [scannedImg, setScannedImg] = useState(null);
  const [matchedImg, setMatchedImg] = useState(null);
  const [error, setError] = useState("");

  const handleMatchFingerprint = async () => {
    setMessage("");
    setMatchedId(null);
    setAlias("");
    setConfidence(null);
    setScannedImg(null);
    setMatchedImg(null);
    setError("");

    try {
      const response = await axios.post(match_url);
      const data = response.data;

      setMessage(data.message);
      setMatchedId(data.id);
      setAlias(data.alias);
      setConfidence(data.confidence);
      setScannedImg(data.scanned_img_str);
      setMatchedImg(data.matched_img_str);
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
          <div style={{ marginTop: "20px" }}>
            <h4>Scanned Image:</h4>
            {scannedImg && (
              <img
                src={`data:image/png;base64,${scannedImg}`}
                alt="Scanned Fingerprint"
                style={{ width: "200px", height: "200px", borderRadius: "10px" }}
              />
            )}
          </div>
          <div style={{ marginTop: "20px" }}>
            <h4>Matched Image:</h4>
            {matchedImg && (
              <img
                src={`data:image/png;base64,${matchedImg}`}
                alt="Matched Fingerprint"
                style={{ width: "200px", height: "200px", borderRadius: "10px" }}
              />
            )}
          </div>
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
