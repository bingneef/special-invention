# DART Workflows

Temporal is the main orchistrator for our data transformation infrastructure. It resides in a generally available namespace and has common activities in place (like generating embeddings, converting documents, etc.). These common activities should listen on the generic queue (i.e. `common`).

Each application can send workflows to a queue _specific_ for that application (i.e. `workflows:elastic`). Each application should provide workers that can process the application workflows. Applications are free to include domain specific activities based on the Temporal workflow (they should listen on `activities:elastic:xxx`). Where possible, activities should store their output in the data owner API (like Documents API). 

## Fundamentals

- The output of an activity should be small (as it's persisted). Blobs should be stored on our storage server with a reference in the activity output. The reference should be something based on the activity input (so that idempotence is maintained). 
- Each activity should be idempotent.
- Any side-effect should be in activities, not in workflows.

## How does temporal work?

Temporal has workflows and activities. A workflow is a python script that essentially calls a set of activities, either in series or parallel. Temporal gives us retries, error handling, state management, timelines, and more for free. Activities are the actual workhorses that do the heavy lifting. They can be called from workflows and can also call other activities.
