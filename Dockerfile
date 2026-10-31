FROM python:3.12-slim

WORKDIR /app

# Run as non-root user for university security compliance
RUN useradd -m polytech
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY openai_engine.py eval_pipeline.py app.py syllabus_electronics_optics.md ./
COPY sample_pdfs/ ./sample_pdfs/

RUN chown -R polytech:polytech /app
USER polytech

EXPOSE 8765
CMD ["python", "-u", "app.py"]
