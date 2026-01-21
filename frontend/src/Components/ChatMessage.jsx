import ChatbotIcon from "./ChatbotIcon";

const ChatMessage = ({ chat }) => {
  // Funzione per formattare il messaggio e gestire blocchi SQL e link speciali
  const formatMessage = (text) => {
    if (!text) return null;

    // Split del messaggio per blocchi SQL
    const parts = text.split(
      /(\*\*(?:Executed|Generated) SQL Query:\*\*\n```sql\n[\s\S]*?\n```)/g
    );

    return parts.map((part, index) => {
      // Verifica se il blocco è SQL
      const sqlMatch = part.match(
        /\*\*((?:Executed|Generated) SQL Query):\*\*\n```sql\n([\s\S]*?)\n```/
      );

      if (sqlMatch) {
        const queryType = sqlMatch[1];
        const sqlCode = sqlMatch[2];

        return (
          <div key={index} className="sql-section">
            <div className="sql-header">
              <span className="sql-icon">📊</span>
              <strong>{queryType}</strong>
              <button
                className="copy-btn"
                onClick={() => navigator.clipboard.writeText(sqlCode)}
                title="Copy SQL Query"
              >
                📋
              </button>
            </div>
            <div className="sql-code-container">
              <pre className="sql-code">
                <code>{sqlCode}</code>
              </pre>
            </div>
          </div>
        );
      } else {
        // Messaggio regolare: supporto HTML per link
        // Se contiene "Download Chat History", intercetta il click
          return (
            <span
              key={index}
              dangerouslySetInnerHTML={{ __html: part }}
            />
          );
      
      }
    });
  };

  return (
    <div className={`message ${chat.role === "model" ? "bot" : "user"}-message`}>
      {chat.role === "model" && <ChatbotIcon />}
      {chat.loading ? (
        <div className="loader"></div>
      ) : (
        <div className="message-text">{formatMessage(chat.text)}</div>
      )}
    </div>
  );
};

export default ChatMessage;
