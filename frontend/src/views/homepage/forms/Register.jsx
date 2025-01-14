import React, { useEffect } from 'react';
import { useState } from 'react';
import axios from 'axios';

function Register() {
    const [message, setMessage] = useState("Please scan your fingerprint in order to register!");
    const [isReady, setIsReady] = useState(false);
    const [name, setName] = useState("");

    const scanFingerprint = () => {
        setTimeout(() => {
            setMessage("Fingerprint successfully registered!");
        }, 3000);
    };

    const handleReset = () => {
        setMessage("Please scan your fingerprint in order to register!");
        setIsReady(false);
    };

    const handleSubmit = async () => {
        try {
            const response = await axios.post("http://localhost:8000/register", {
                name: name,
                isReady: isReady,
            });

            console.log("Response from server:", response.data);
        } catch (error) {
            console.error("Error while sending data to the server:", error);
        }
    };

    useEffect(() => {
        scanFingerprint();
    }, [message]);

    return (
        <div>
            <h2>Register</h2>
            <label>
                {message}
            </label>
            <p></p>
            <label>
                Name:
                <input
                    type="text"
                    name="name"
                    onChange={(e) => { setName(e.target.value); }}
                />
            </label>
            <br />
            <button onClick={handleSubmit}>Submit</button>
            <button onClick={handleReset}>Reset</button>
        </div>
    );
}

export default Register;
