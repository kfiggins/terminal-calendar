# Terminal Calendar Schedule Format

## JSON Schema for LLM Schedule Generation

When generating schedules for Terminal Calendar, use the following JSON format:

```json
{
  "date": "YYYY-MM-DD",
  "tasks": [
    {
      "id": "unique_task_id",
      "title": "Task title",
      "start_time": "HH:MM",
      "end_time": "HH:MM",
      "description": "Brief description of the task",
      "priority": "high|medium|low"
    }
  ]
}
```

## Field Specifications

### Root Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `date` | string | Yes | Schedule date in ISO format (YYYY-MM-DD) |
| `tasks` | array | Yes | Array of task objects |

### Task Object

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | string | Yes | Unique identifier for the task | `"standup_morning"`, `"task_1"` |
| `title` | string | Yes | Brief, descriptive task name | `"Morning standup"`, `"Deep work session"` |
| `start_time` | string | Yes | Task start time in 24-hour format (HH:MM) | `"09:00"`, `"14:30"` |
| `end_time` | string | Yes | Task end time in 24-hour format (HH:MM) | `"10:00"`, `"15:00"` |
| `description` | string | No | Detailed description or notes | `"Daily team sync - discuss blockers"` |
| `priority` | string | Yes | Task priority level | `"high"`, `"medium"`, `"low"` |

## Priority Levels

- **`high`**: Critical tasks, deadlines, important meetings (displayed in red with !!!)
- **`medium`**: Regular work, routine tasks (displayed in yellow with !!)
- **`low`**: Optional tasks, breaks, nice-to-haves (displayed in green with !)

## Best Practices

### Time Format
- Use 24-hour format (HH:MM) for all times
- Valid: `"09:00"`, `"14:30"`, `"23:45"`
- Invalid: `"9:00"`, `"2:30 PM"`, `"9am"`

### Task IDs
- Make them descriptive and unique
- Good: `"standup_morning"`, `"deepwork_feature_x"`, `"lunch_break"`
- Acceptable: `"task_1"`, `"task_2"`, `"task_3"`

### Scheduling Tips
- Add 5-10 minute buffers between tasks for transitions
- Include breaks (mark as low priority)
- Be realistic with time estimates
- Avoid overlapping tasks
- Tasks should be at least 5 minutes long
- Avoid tasks longer than 4 hours without breaks

### Date Format
- Always use ISO format: YYYY-MM-DD
- Examples: `"2024-03-15"`, `"2024-12-01"`
- The date should match the day you're scheduling

## Complete Example

See [examples/sample_schedule.json](examples/sample_schedule.json) for a full working example with 9 tasks covering a typical workday.

```json
{
  "date": "2024-03-15",
  "tasks": [
    {
      "id": "standup_morning",
      "title": "Morning standup",
      "start_time": "09:00",
      "end_time": "09:15",
      "description": "Daily team sync - discuss blockers and priorities",
      "priority": "high"
    },
    {
      "id": "deepwork_session",
      "title": "Deep work: Feature implementation",
      "start_time": "09:30",
      "end_time": "11:30",
      "description": "Focus session - implement core functionality",
      "priority": "high"
    },
    {
      "id": "coffee_break",
      "title": "Coffee break",
      "start_time": "11:30",
      "end_time": "11:45",
      "description": "Take a break, stretch, refill water",
      "priority": "low"
    },
    {
      "id": "lunch",
      "title": "Lunch",
      "start_time": "12:30",
      "end_time": "13:30",
      "description": "Lunch break - step away from desk",
      "priority": "medium"
    },
    {
      "id": "client_meeting",
      "title": "Client meeting",
      "start_time": "14:00",
      "end_time": "14:30",
      "description": "Project status update with stakeholders",
      "priority": "high"
    }
  ]
}
```

## Validation

The schedule will be automatically validated when loaded. Common issues detected:

- **Overlapping tasks**: Two tasks scheduled at the same time
- **Large gaps**: More than 2 hours between tasks
- **Short tasks**: Tasks shorter than 5 minutes
- **Long tasks**: Tasks longer than 4 hours
- **Invalid times**: Malformed time strings or end time before start time

Use `tcal validate schedule.json` to check a schedule before loading it.

## LLM Prompt Template

When asking an LLM to generate a schedule, you can use:

```
Create a daily schedule in JSON format for [DATE] with the following tasks:
- [Task description with approximate duration and priority]
- [Task description with approximate duration and priority]
- ...

Use this exact JSON structure:
{
  "date": "YYYY-MM-DD",
  "tasks": [
    {
      "id": "unique_id",
      "title": "Task name",
      "start_time": "HH:MM",
      "end_time": "HH:MM",
      "description": "Brief description",
      "priority": "high|medium|low"
    }
  ]
}

Requirements:
- Use 24-hour time format (HH:MM)
- Include 5-10 minute buffers between tasks
- Make task IDs descriptive (e.g., "standup_morning" not "task1")
- Assign appropriate priorities: high (critical/deadlines), medium (regular work), low (breaks/optional)
- Output only the JSON, no additional text
```

## Loading Your Schedule

Once generated, load the schedule with:

```bash
tcal load schedule.json
tcal view
```
