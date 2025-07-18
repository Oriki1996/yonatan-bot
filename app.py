# app.py - תיקון endpoint /api/chat - הוסף זאת במקום הקוד הקיים

@app.route('/api/chat', methods=['POST'])
@limiter.limit("30 per minute")
def chat():
    """Enhanced chat endpoint with proper validation and streaming response"""
    try:
        # Enhanced request validation
        if not request.is_json:
            return jsonify({"error": "הבקשה חייבת להיות בפורמט JSON"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"error": "נתוני JSON חסרים"}), 400

        # Validate required fields
        session_id = data.get('session_id')
        message = data.get('message')
        
        if not session_id:
            return jsonify({"error": "שדה session_id חסר"}), 400
        if not message:
            return jsonify({"error": "שדה message חסר"}), 400
        
        # Enhanced validation
        if not validate_session_id(session_id):
            return jsonify({"error": "session_id לא תקין"}), 400
            
        if not isinstance(message, str) or not message.strip():
            return jsonify({"error": "שדה message לא תקין"}), 400
            
        if len(message) > app.config.get('MAX_MESSAGE_LENGTH', 5000):
            return jsonify({"error": "ההודעה ארוכה מדי"}), 400

        # Enhanced security checks
        if is_suspicious_request():
            log_security_event("suspicious_chat_request", {
                "session_id": session_id[:8] + "...",
                "message_length": len(message)
            })
            return jsonify({"error": "בקשה חשודה נחסמה"}), 403

        # Sanitize message
        message = sanitize_input(message)
        if not message:
            return jsonify({"error": "הודעה לא תקינה אחרי ניקוי"}), 400

        # Get or create session data
        try:
            # Try to get questionnaire data for this session
            questionnaire_data = {}
            if session_id:
                questionnaire = QuestionnaireResponse.query.filter_by(parent_id=session_id).first()
                if questionnaire:
                    questionnaire_data = questionnaire.get_response_data()

            # Check if conversation exists, if not create one
            parent = Parent.query.filter_by(id=session_id).first()
            if parent:
                # Find or create active conversation
                conversation = Conversation.query.filter_by(
                    parent_id=session_id,
                    status='active'
                ).first()
                
                if not conversation:
                    # Create new conversation
                    conversation = Conversation(
                        parent_id=session_id,
                        child_id=parent.children[0].id if parent.children else None,
                        topic=questionnaire_data.get('main_challenge', 'שיחה כללית')
                    )
                    db.session.add(conversation)
                    db.session.flush()  # Get ID without committing

                # Add user message to conversation (except for START_CONVERSATION)
                if message != "START_CONVERSATION":
                    user_message = Message(
                        conversation_id=conversation.id,
                        sender_type='user',
                        content=message
                    )
                    db.session.add(user_message)

        except Exception as db_error:
            logger.error(f"Database error in chat: {db_error}")
            # Continue without database - let fallback handle it

        # Function to generate streaming response
        def generate_response():
            try:
                # Try AI response first
                if model:
                    try:
                        # Build enhanced context
                        context = ""
                        if questionnaire_data:
                            context = f"""
הורה: {questionnaire_data.get('parent_name', 'הורה')}
ילד/ה: {questionnaire_data.get('child_name', 'ילד/ה')} בן/בת {questionnaire_data.get('child_age', 'לא ידוע')}
אתגר עיקרי: {questionnaire_data.get('main_challenge', 'לא צוין')}
רמת מצוקה: {questionnaire_data.get('distress_level', 'לא צוין')}/10
ניסיונות קודמים: {questionnaire_data.get('past_solutions', 'לא צוין')}
מטרת השיחה: {questionnaire_data.get('goal', 'לא צוין')}
"""

                        prompt = f"""
אתה יונתן, פסיכו-בוט חינוכי מתקדם המתמחה בהורות למתבגרים ומבוסס על עקרונות CBT.

{context}

עקרונות התגובה שלך:
1. הגב בעברית בלבד עם טון חם, תומך ומקצועי
2. השתמש בעקרונות CBT: זיהוי מחשבות, אתגור אמונות, שינוי התנהגות
3. תן כלים פרקטיים ומעשיים שאפשר ליישם מיד
4. השתמש בפורמט CARD[כותרת|תוכן] לטיפים חשובים
5. הוסף כפתורי הצעה בפורמט [טקסט כפתור] לפעולות נוספות
6. התמקד בפתרונות ולא בבעיות
7. הכר ברגשות ההורה ותן legitimacy למצוקה
8. תן דוגמאות קונקרטיות ומעשיות

הודעת המשתמש: {message}
"""

                        # Generate AI response with streaming
                        response = model.generate_content(prompt)
                        
                        if response and response.text:
                            full_response = response.text
                            
                            # Save bot message to conversation
                            try:
                                if 'conversation' in locals():
                                    bot_message = Message(
                                        conversation_id=conversation.id,
                                        sender_type='bot',
                                        content=full_response
                                    )
                                    db.session.add(bot_message)
                                    conversation.update_message_count()
                                    db.session.commit()
                            except Exception as save_error:
                                logger.warning(f"Could not save message to DB: {save_error}")
                                db.session.rollback()
                            
                            # Stream the response in chunks
                            chunk_size = 50
                            for i in range(0, len(full_response), chunk_size):
                                chunk = full_response[i:i+chunk_size]
                                yield chunk
                            return
                            
                    except Exception as ai_error:
                        logger.error(f"AI model error: {ai_error}")
                        # Fall through to fallback system

                # Use fallback system
                if advanced_fallback_system:
                    fallback_response = advanced_fallback_system.get_fallback_response(
                        message, session_id, questionnaire_data
                    )
                    
                    # Save fallback response to conversation
                    try:
                        if 'conversation' in locals():
                            bot_message = Message(
                                conversation_id=conversation.id,
                                sender_type='bot',
                                content=fallback_response
                            )
                            db.session.add(bot_message)
                            conversation.update_message_count()
                            db.session.commit()
                    except Exception as save_error:
                        logger.warning(f"Could not save fallback message to DB: {save_error}")
                        db.session.rollback()
                    
                    # Stream fallback response
                    chunk_size = 50
                    for i in range(0, len(fallback_response), chunk_size):
                        chunk = fallback_response[i:i+chunk_size]
                        yield chunk
                    return
                
                # Last resort - basic response
                basic_response = f"שלום! אני יונתן. מצטער, יש לי קושי טכני כרגע, אבל אני כאן לעזור לך. איך אני יכול לסייע?"
                yield basic_response
                
            except Exception as e:
                logger.error(f"Error in generate_response: {e}")
                error_response = "מצטער, אירעה שגיאה טכנית. אנא נסה שוב."
                yield error_response

        # Return streaming response
        return Response(
            generate_response(),
            mimetype='text/plain',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'  # Disable Nginx buffering
            }
        )

    except ValidationError as e:
        return jsonify({"error": "נתונים לא תקינים", "details": e.messages}), 400
    except BotError as e:
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}")
        error = handle_generic_error(e)
        return jsonify(error.to_dict()), error.status_code