# Usage Guide

## Configuration

Configuration files are located in `mltune/config/`.

### Defining Coefficients

Edit `COEFFICIENT_TUNING.py` to specify tunable parameters:

```python
COEFFICIENTS = [
    {
        'name': 'k1',
        'bounds': (0.0, 1.0),
        'initial': 0.5
    },
    # Additional coefficients...
]
```

### System Behavior

Edit `TUNER_TOGGLES.ini` to control tuning behavior:

```ini
[tuning]
autotune_enabled = False          # Enable automatic optimization
auto_advance_on_success = False   # Advance to next coefficient automatically
shot_threshold = 10               # Minimum shots before optimization

[network]
team_number = 1234
server_ip = 10.12.34.2
```

## Operation

### Standard Workflow

1. Launch the tuner application
2. Enable tuning via dashboard toggle
3. Perform shots and provide hit/miss feedback
4. Trigger optimization when sufficient data is collected
5. Evaluate new coefficients
6. Advance to next coefficient when satisfied

### Operating Modes

**Manual Mode** (Recommended):
- User-controlled optimization timing
- User-controlled coefficient advancement
- Set both `autotune_enabled` and `auto_advance_on_success` to `False`

**Automatic Mode**:
- Automatic optimization after N shots
- Automatic advancement on success
- Set both toggles to `True`

## Web Dashboard

Access the dashboard at http://localhost:8050.

Available functions:
- Enable/disable tuning
- View current coefficient values
- Access optimization history
- Manual optimization control
- Coefficient navigation
- Log viewing and shot data analysis

The dashboard updates automatically when new data is received from the robot.

## Troubleshooting

### Connection Issues

**Symptom**: "Disconnected" status in GUI

**Solutions**:
- Verify robot is powered and operational
- Confirm team number in configuration
- Check network connection to robot

### Import Errors

**Symptom**: Module import failures

**Solutions**:
- Verify start script was executed
- Manual installation: `pip install -r mltune/tuner/requirements.txt`

### Optimization Delays

**Symptom**: Extended optimization duration

**Solutions**:
- Reduce shot threshold in configuration
- Verify shot data is being logged correctly
- Monitor logs for diagnostic information

## Recommendations

- Begin with wide parameter bounds, then narrow based on initial results
- Collect 10-20 shots per coefficient for reliable optimization
- Monitor application logs for system status
- Use the dashboard for all control operations
- Back up optimized coefficients before parameter resets

## Logging

Logs are stored in `tuner_logs/` with timestamps. Review logs for troubleshooting and analysis.
