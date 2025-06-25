#!/bin/bash
echo "🔄 Last Trade Activity: $(tail -1 /tmp/trades.log | cut -c1-50)..."
echo "🔄 Last Deal Activity: $(tail -1 /tmp/deals.log | cut -c1-50)..."
