#!/bin/bash

set -e

echo "🚀 Deploy su Koyeb - Agriturismo Backend"

# Colori per output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Verifica prerequisiti
check_prerequisites() {
    print_status "Controllo prerequisiti..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker non trovato. Installa Docker Desktop."
        exit 1
    fi
    
    if ! command -v koyeb &> /dev/null; then
        print_warning "Koyeb CLI non trovato. Installazione..."
        curl -fsSL https://cli.koyeb.com/install.sh | bash
        source ~/.bashrc
    fi
    
    print_status "Prerequisiti verificati"
}

# Login Koyeb
login_koyeb() {
    print_status "Login su Koyeb..."
    
    if ! koyeb account whoami &> /dev/null; then
        print_warning "Login richiesto. Apri il browser per autenticarti..."
        koyeb auth login
    fi
    
    print_status "Login Koyeb completato"
}

# Build e push Docker image
build_and_push() {
    print_status "Build Docker image..."
    
    # Build image
    docker build -t agriturismo-backend .
    
    # Tag per Koyeb
    docker tag agriturismo-backend koyeb/agriturismo-backend:latest
    
    print_status "Docker image buildata"
}

# Deploy su Koyeb
deploy_koyeb() {
    print_status "Deploy su Koyeb..."
    
    # Crea app su Koyeb
    koyeb app init agriturismo-backend \
        --docker koyeb/agriturismo-backend:latest \
        --ports 8000:http \
        --routes /:8000 \
        --env DATABASE_URL="$DATABASE_URL" \
        --env SECRET_KEY="$SECRET_KEY" \
        --env CORS_ORIGINS="$CORS_ORIGINS" \
        --env ENABLE_SSL_REDIRECT="True"
    
    print_status "Deploy Koyeb completato"
}

# Health check
health_check() {
    print_status "Verifica health check..."
    
    # Aspetta che l'app sia pronta
    sleep 30
    
    # Ottieni URL dell'app
    APP_URL=$(koyeb app get agriturismo-backend --output json | jq -r '.app.routes[0].url')
    
    # Test health endpoint
    if curl -f -s "$APP_URL/health" > /dev/null; then
        print_status "Health check OK"
        echo -e "🌐 App disponibile su: ${GREEN}$APP_URL${NC}"
    else
        print_error "Health check fallito"
        exit 1
    fi
}

# Main execution
main() {
    check_prerequisites
    login_koyeb
    build_and_push
    deploy_koyeb
    health_check
    
    print_status "🎉 Deploy completato con successo!"
}

# Esegui con gestione errori
if main; then
    exit 0
else
    print_error "Deploy fallito"
    exit 1
fi 