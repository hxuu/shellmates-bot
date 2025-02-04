# **Roadmap for AI-Powered Smart Scheduling in Discord Bot**

---

## **Phase 1: Data Collection and Storage (Person 1)**  

### **Tasks:**  
1. **Track User Activity:**  
   - Use the `on_member_update` event in `discord.py` to capture online/offline status.  
   - Collect and store user availability preferences (timezones, preferred meeting times).  

2. **Choose and Set Up Storage:**  
   - Implement **SQLite** for structured, concurrent data storage.  
   - Set up a schema with tables for user activity and scheduling preferences.  
   - Provide fallback support for JSON-based storage for simpler scenarios.  

3. **Secure Data Handling:**  
   - Use the **dotenv** package to handle secure configurations.  

### **Deliverables:**  
- Data tracking and storage system with SQLite integration.  
- A secure and scalable database schema.  

---

## **Phase 2: AI Model Integration (Person 2)**  

### **Tasks:**  
1. **Initial Heuristic Scheduling:**  
   - Implement KMeans clustering (`scikit-learn`) to find optimal meeting time slots.  
   - Rank suggestions based on user availability and past attendance patterns.  

2. **Model Fine-Tuning:**  
   - Use **Facebook Prophet** or `neuralprophet` for predicting future activity trends based on historical data.  
   - Train the model using collected user activity datasets.  

3. **Model Evaluation:**  
   - Test the model with real user data.  
   - Adjust hyperparameters for better accuracy.  

### **Deliverables:**  
- KMeans-based scheduling algorithm.  
- Prophet-based prediction model for future scheduling.  
- Model evaluation and documentation.  

---

## **Phase 3: Bot Integration and Command Handling (Person 3)**  

### **Tasks:**  
1. **Command Design:**  
   - Create commands such as:  
     - `/schedule_meeting`: Suggest meeting times based on AI recommendations.  
     - `/set_availability`: Allow users to input their availability preferences.  

2. **Bot Responses and Visualization:**  
   - Present AI suggestions using **Discord embeds** for clean visualization.  
   - Handle user confirmations for meeting scheduling.  

3. **Performance Optimization:**  
   - Use **asyncio** for asynchronous operations to avoid blocking the bot.  
   - Implement error handling and fallback logic.  

### **Deliverables:**  
- Command-based interaction system for scheduling.  
- Optimized and responsive bot commands.  
- Visual output with Discord embeds.  

---

## **Phase 4: Testing and Deployment (Collaborative)**  

### **Tasks:**  
1. Unit and integration testing using **pytest** and **pytest-asyncio**.  
2. Performance testing with real users to validate AI scheduling logic.  
3. Final deployment and maintenance strategy.