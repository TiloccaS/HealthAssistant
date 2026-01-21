import { useRef, useEffect, useState } from "react"; // Modified import

const API_BASE = `http://localhost:${import.meta.env.VITE_API_PORT || 8000}`;

const ChatForm = ({
  setChatHistory,
  generateBotResponse,
  isWaitingForResponse,
}) => {
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [pendingPdfPath, setPendingPdfPath] = useState(null);  // Store uploaded PDF path for analysis

  // Add useEffect to focus input when isWaitingForResponse changes to false
  useEffect(() => {
    if (!isWaitingForResponse && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isWaitingForResponse]);

  const handleSubmit = async (e) => {
    e.preventDefault();//default reload the browser. this line avoid it
    const userMessage = inputRef.current.value.trim();//take input
    if (!userMessage) return;
    inputRef.current.value = ""; // Clear the input field

    // Check if user is confirming PDF analysis
    if (pendingPdfPath) {
      const confirmWords = ['yes', 'si', 'sì', 'ok', 'analyze', 'analizza', 'confirm', 'conferma', 'please', 'per favore'];
      const rejectWords = ['no', 'cancel', 'annulla', 'skip', 'salta'];
      
      const msgLower = userMessage.toLowerCase();
      
      if (confirmWords.some(word => msgLower.includes(word))) {
        // User confirmed - analyze the PDF
        setChatHistory((history) => [
          ...history,
          { role: "user", text: userMessage },
          { role: "model", text: "Analyzing your laboratory report... Please wait.", loading: true },
        ]);
        
        try {
          const response = await fetch(`${API_BASE}/api/analyze-lab-report`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_path: pendingPdfPath }),
            credentials: 'include', // Include cookies/session
          });
          const data = await response.json();
          setChatHistory((history) => {
            const newHistory = history.filter(msg => !msg.loading);
            return [
              ...newHistory,
              { role: "model", text: data.analysis || "Could not analyze the document." },
            ];
          });
        } catch (error) {
          setChatHistory((history) => {
            const newHistory = history.filter(msg => !msg.loading);
            return [
              ...newHistory,
              { role: "model", text: ` Analysis error: ${error.message}` },
            ];
          });
        }
        
        setPendingPdfPath(null);
        return;
      } else if (rejectWords.some(word => msgLower.includes(word))) {
        // User declined analysis
        setChatHistory((history) => [
          ...history,
          { role: "user", text: userMessage },
          { role: "model", text: "No problem! The document has been saved. Let me know if you need anything else." },
        ]);
        setPendingPdfPath(null);
        return;
      }
      // If neither confirm nor reject, continue with normal flow but clear pending
      setPendingPdfPath(null);
    }

    // Update chat history with user input
    setChatHistory((history) => [
      ...history,
      { role: "user", text: userMessage },
    ]);

    // Add a thinking placeholder for the bot response
    requestAnimationFrame(() => {
      setChatHistory((history) => [
        ...history,
        { role: "model", loading: true },
      ]);
    });

    // Send only the user message text to the WebSocket handler
    setTimeout(() => {
      generateBotResponse(userMessage);
    }, 100);
  };

  const MAX_FILE_SIZE = 2 * 1024 * 1024; // 2MB in bytes

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Check file size limit
    if (file.size > MAX_FILE_SIZE) {
      setChatHistory((history) => [
        ...history,
        { role: "user", text: `Trying to upload: ${file.name}` },
        { role: "model", text: `File too large! Maximum size is 2MB.\n\nYour file: ${(file.size / (1024 * 1024)).toFixed(2)}MB` },
      ]);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      return;
    }

    const isPdf = file.name.toLowerCase().endsWith('.pdf');
    setIsUploading(true);

    // Show uploading message in chat
    setChatHistory((history) => [
      ...history,
      { role: "user", text: `Uploading: ${file.name}` },
    ]);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('description', `Uploaded from chat: ${file.name}`);

    try {
      const response = await fetch(`${API_BASE}/api/upload-document`, {
        method: 'POST',
        body: formData,
        credentials: 'include', // Include cookies/session
      });

      const data = await response.json();

      if (response.ok) {
        if (isPdf) {
          // For PDF files, ask if user wants analysis
          setPendingPdfPath(data.file_path);
          setChatHistory((history) => [
            ...history,
            { role: "model", text: `Laboratory report uploaded successfully!\n\n ${data.filename}\n\n Would you like me to analyze this lab report and provide advice?\n\nReply "Yes" to analyze or "No" to skip.` },
          ]);
        } else {
          // For other files, just confirm upload
          setChatHistory((history) => [
            ...history,
            { role: "model", text: `Document uploaded successfully!\n\nFilename: ${data.filename}\n\nYour document has been saved to your medical records.` },
          ]);
        }
      } else {
        setChatHistory((history) => [
          ...history,
          { role: "model", text: `Upload failed: ${data.error}` },
        ]);
      }
    } catch (error) {
      setChatHistory((history) => [
        ...history,
        { role: "model", text: `Upload error: ${error.message}` },
      ]);
    }

    setIsUploading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };//open file browser 

  return (
    <form action="#" className="chat-form" onSubmit={handleSubmit}>
      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        accept=".png,.jpg,.jpeg,.gif,.pdf,.doc,.docx"
        style={{ display: 'none' }}
      />
      
      {/* Upload button */}
      <button
        type="button"
        className="material-symbols-rounded upload-btn"
        onClick={triggerFileInput}
        disabled={isWaitingForResponse || isUploading}
        title="Upload document"
        style={{ 
          marginRight: '8px',
          opacity: (isWaitingForResponse || isUploading) ? 0.5 : 1,
          cursor: (isWaitingForResponse || isUploading) ? 'not-allowed' : 'pointer'
        }}
      >
        {isUploading ? 'hourglass_empty' : 'attach_file'}
      </button>

      <input
        type="text"
        ref={inputRef}
        placeholder="Type your message..."
        className="message-input"
        required
        disabled={isWaitingForResponse} // Add this line
      />
      <button
        className="material-symbols-rounded"
        disabled={isWaitingForResponse}
      >
        arrow_upward
      </button>{" "}
      {/* Add disabled prop here too */}
    </form>
  );
};

export default ChatForm;
