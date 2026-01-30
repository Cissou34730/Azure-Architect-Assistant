
> frontend@1.0.0 lint
> eslint --report-unused-disable-directives


C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\components\diagrams\hooks\useMermaidRenderer.ts
  23:8   error    Function 'useMermaidRenderer' has too many lines (55). Maximum allowed is 50                                                                             max-lines-per-function
  44:22  error    Do not use 'as' assertions. Prefer precise types or type guards                                                                                          no-restricted-syntax
  44:22  error    Unsafe type assertion: type 'RefObject<HTMLDivElement | null>' is more narrow than the original type                                                     @typescript-eslint/no-unsafe-type-assertion
  44:22  error    Do not use 'as' assertions. Prefer precise types or type guards                                                                                          no-restricted-syntax
  44:29  warning  Don't use `unknown` as a type. Avoid 'unknown' in internal code. Use domain types; reserve 'unknown' for external boundaries (I/O, JSON, external APIs)  @typescript-eslint/no-restricted-types
  54:9   error    Unexpected nullable string value in conditional. Please handle the nullish/empty cases explicitly                                                        @typescript-eslint/strict-boolean-expressions

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\config\featureFlags.ts
  6:29  error  Do not use 'as' assertions. Prefer precise types or type guards  no-restricted-syntax

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\components\ChatPanel\MessageItem.tsx
   8:1   error  Function 'messageEqual' has a complexity of 11. Maximum allowed is 10                       complexity
  25:14  error  Variable name `MessageItem` must match one of the following formats: camelCase, UPPER_CASE  @typescript-eslint/naming-convention

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\components\deliverables\CostBreakdown.tsx
   10:7   error  Variable name `CostPieChart` must match one of the following formats: camelCase, UPPER_CASE    @typescript-eslint/naming-convention
  140:7   error  Variable name `LineItemsTable` must match one of the following formats: camelCase, UPPER_CASE  @typescript-eslint/naming-convention
  193:19  error  Object Literal Method name `TableRow` must match one of the following formats: camelCase       @typescript-eslint/naming-convention
  329:1   error  File has too many lines (340). Maximum allowed is 300                                          max-lines

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\components\deliverables\DiagramGallery.tsx
   65:7   error  Variable name `DiagramCard` must match one of the following formats: camelCase, UPPER_CASE  @typescript-eslint/naming-convention
  192:21  error  Unexpected string value in conditional. An explicit empty string check is required          @typescript-eslint/strict-boolean-expressions
  193:21  error  Unexpected string value in conditional. An explicit empty string check is required          @typescript-eslint/strict-boolean-expressions

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\components\deliverables\IacViewer.tsx
    8:7  error  Variable name `SyntaxHighlighter` must match one of the following formats: camelCase, UPPER_CASE  @typescript-eslint/naming-convention
  147:1  error  Function 'CodeViewer' has too many lines (101). Maximum allowed is 100                            max-lines-per-function
  329:1  error  File has too many lines (326). Maximum allowed is 300                                             max-lines

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\components\deliverables\adrlib\AdrGrid.tsx
  24:7  error  Variable name `AdrGridItem` must match one of the following formats: camelCase, UPPER_CASE  @typescript-eslint/naming-convention

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\components\deliverables\adrlib\AdrTable.tsx
  23:7   error  Variable name `AdrTableItem` must match one of the following formats: camelCase, UPPER_CASE  @typescript-eslint/naming-convention
  98:13  error  Object Literal Method name `TableRow` must match one of the following formats: camelCase     @typescript-eslint/naming-convention
  99:39  error  'data-index' is missing in props validation                                                  react/prop-types

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\components\overview\ActivityTimeline.tsx
  125:11  error  Unnecessary conditional, value is always falsy                        @typescript-eslint/no-unnecessary-condition
  125:12  error  Unexpected object value in conditional. The condition is always true  @typescript-eslint/strict-boolean-expressions

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\components\overview\RequirementsCard.tsx
  66:7  error  Variable name `RequirementItem` must match one of the following formats: camelCase, UPPER_CASE  @typescript-eslint/naming-convention

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\components\unified\LeftContextPanel\RequirementsTab.tsx
  15:6   warning  React Hook useMemo has a missing dependency: 'requirements'. Either include it or remove the dependency array        react-hooks/exhaustive-deps
  18:11  error    Unsafe assignment of an `any` value                                                                                  @typescript-eslint/no-unsafe-assignment
  18:22  error    Unsafe call of an `any` typed value                                                                                  @typescript-eslint/no-unsafe-call
  18:41  error    Unsafe member access .filter on an `any` value                                                                       @typescript-eslint/no-unsafe-member-access
  18:55  error    Unsafe call of an `any` typed value                                                                                  @typescript-eslint/no-unsafe-call
  18:57  error    Unsafe member access .category on an `any` value                                                                     @typescript-eslint/no-unsafe-member-access
  19:11  error    Unsafe assignment of an `any` value                                                                                  @typescript-eslint/no-unsafe-assignment
  19:24  error    Unsafe call of an `any` typed value                                                                                  @typescript-eslint/no-unsafe-call
  19:43  error    Unsafe member access .filter on an `any` value                                                                       @typescript-eslint/no-unsafe-member-access
  19:57  error    Unsafe call of an `any` typed value                                                                                  @typescript-eslint/no-unsafe-call
  19:59  error    Unsafe member access .category on an `any` value                                                                     @typescript-eslint/no-unsafe-member-access
  20:11  error    Unsafe assignment of an `any` value                                                                                  @typescript-eslint/no-unsafe-assignment
  20:17  error    Unsafe call of an `any` typed value                                                                                  @typescript-eslint/no-unsafe-call
  20:36  error    Unsafe member access .filter on an `any` value                                                                       @typescript-eslint/no-unsafe-member-access
  20:50  error    Unsafe call of an `any` typed value                                                                                  @typescript-eslint/no-unsafe-call
  20:52  error    Unsafe member access .category on an `any` value                                                                     @typescript-eslint/no-unsafe-member-access
  21:11  error    Unsafe assignment of an `any` value                                                                                  @typescript-eslint/no-unsafe-assignment
  21:19  error    Unsafe call of an `any` typed value                                                                                  @typescript-eslint/no-unsafe-call
  21:38  error    Unsafe member access .filter on an `any` value                                                                       @typescript-eslint/no-unsafe-member-access
  22:13  error    Unsafe assignment of an `any` value                                                                                  @typescript-eslint/no-unsafe-assignment
  22:19  error    Unsafe call of an `any` typed value                                                                                  @typescript-eslint/no-unsafe-call
  22:21  error    Unsafe member access .category on an `any` value                                                                     @typescript-eslint/no-unsafe-member-access
  27:28  error    Unsafe assignment of an `any` value                                                                                  @typescript-eslint/no-unsafe-assignment
  28:30  error    Unsafe assignment of an `any` value                                                                                  @typescript-eslint/no-unsafe-assignment
  29:34  error    Unsafe assignment of an `any` value                                                                                  @typescript-eslint/no-unsafe-assignment
  30:25  error    Unsafe assignment of an `any` value                                                                                  @typescript-eslint/no-unsafe-assignment
  31:27  error    Unsafe member access .length on an `any` value                                                                       @typescript-eslint/no-unsafe-member-access
  34:41  error    Unsafe return of a value of type `any`                                                                               @typescript-eslint/no-unsafe-return
  35:36  error    Unsafe return of a value of type `any`                                                                               @typescript-eslint/no-unsafe-return
  35:44  error    Unsafe member access .length on an `any` value                                                                       @typescript-eslint/no-unsafe-member-access
  38:6   warning  React Hook useMemo has a missing dependency: 'sortedRequirements'. Either include it or remove the dependency array  react-hooks/exhaustive-deps
  70:17  error    Unsafe assignment of an `any` value                                                                                  @typescript-eslint/no-unsafe-assignment
  76:20  error    Invalid operand for a '+' operation. Operands must each be a number or string. Got `any`                             @typescript-eslint/restrict-plus-operands
  87:22  error    Unsafe member access .text on an `any` value                                                                         @typescript-eslint/no-unsafe-member-access

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\components\unified\LeftContextPanel\TabContent.tsx
  38:14  error  Variable name `TabContent` must match one of the following formats: camelCase, UPPER_CASE  @typescript-eslint/naming-convention

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\components\unified\RightDeliverablesPanel\AdrsSection.tsx
  41:14  error  Variable name `AdrsSection` must match one of the following formats: camelCase, UPPER_CASE  @typescript-eslint/naming-convention

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\components\unified\RightDeliverablesPanel\CostsSection.tsx
  41:14  error  Variable name `CostsSection` must match one of the following formats: camelCase, UPPER_CASE  @typescript-eslint/naming-convention

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\components\unified\RightDeliverablesPanel\DiagramsSection.tsx
  53:14  error  Variable name `DiagramsSection` must match one of the following formats: camelCase, UPPER_CASE  @typescript-eslint/naming-convention

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\components\unified\RightDeliverablesPanel\FindingsSection.tsx
  39:14  error  Variable name `FindingsSection` must match one of the following formats: camelCase, UPPER_CASE  @typescript-eslint/naming-convention

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\components\workspace\ChatPanel.tsx
   20:8   error  Function 'ChatPanel' has too many lines (167). Maximum allowed is 100                   max-lines-per-function
   42:10  error  Unexpected nullable object value in conditional. An explicit null check is required     @typescript-eslint/strict-boolean-expressions
   69:9   error  Variable name `Header` must match one of the following formats: camelCase, UPPER_CASE   @typescript-eslint/naming-convention
   70:10  error  Unexpected nullable object value in conditional. An explicit null check is required     @typescript-eslint/strict-boolean-expressions
   92:9   error  Variable name `Footer` must match one of the following formats: camelCase, UPPER_CASE   @typescript-eslint/naming-convention
  157:15  error  Object Literal Method name `Header` must match one of the following formats: camelCase  @typescript-eslint/naming-convention
  158:15  error  Object Literal Method name `Footer` must match one of the following formats: camelCase  @typescript-eslint/naming-convention

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\hooks\useChat.ts
  10:24  error  Arrow function has too many lines (55). Maximum allowed is 50                                      max-lines-per-function
  36:9   error  Unexpected nullable string value in conditional. Please handle the nullish/empty cases explicitly  @typescript-eslint/strict-boolean-expressions

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\hooks\useChatMessaging.ts
   85:8   error  Function 'useChatMessaging' has too many lines (167). Maximum allowed is 50                        max-lines-per-function
  100:9   error  Unexpected nullable string value in conditional. Please handle the nullish/empty cases explicitly  @typescript-eslint/strict-boolean-expressions
  109:46  error  Async arrow function has a complexity of 12. Maximum allowed is 10                                 complexity
  130:29  error  Unexpected nullable string value in conditional. Please handle the nullish/empty cases explicitly  @typescript-eslint/strict-boolean-expressions
  239:1   error  File has too many lines (236). Maximum allowed is 200                                              max-lines

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\hooks\useProjectDetails.ts
  13:8  error  Function 'useProjectDetails' has too many lines (76). Maximum allowed is 50  max-lines-per-function

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\hooks\useProjectOperations.ts
  23:8  error  Function 'useProjectOperations' has too many lines (53). Maximum allowed is 50  max-lines-per-function

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\features\projects\hooks\useProposal.ts
  20:28  error  Arrow function has too many lines (51). Maximum allowed is 50  max-lines-per-function

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\hooks\useIntersectionObserver.ts
  22:10  error  Unexpected nullable object value in conditional. An explicit null check is required  @typescript-eslint/strict-boolean-expressions

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\services\chatService.ts
  16:9   error  Unexpected nullable string value in conditional. Please handle the nullish/empty cases explicitly  @typescript-eslint/strict-boolean-expressions
  36:17  error  Unexpected nullable string value in conditional. Please handle the nullish/empty cases explicitly  @typescript-eslint/strict-boolean-expressions

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\utils\mermaidConfig.ts
   7:7   error  Unexpected nullable object value in conditional. An explicit null check is required  @typescript-eslint/strict-boolean-expressions
   8:7   error  Unexpected nullable object value in conditional. An explicit null check is required  @typescript-eslint/strict-boolean-expressions
  34:12  error  Unexpected nullable object value in conditional. An explicit null check is required  @typescript-eslint/strict-boolean-expressions

C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend\src\utils\messageArchive.ts
  46:19  warning  Don't use `unknown` as a type. Avoid 'unknown' in internal code. Use domain types; reserve 'unknown' for external boundaries (I/O, JSON, external APIs)  @typescript-eslint/no-restricted-types
  48:32  warning  Don't use `unknown` as a type. Avoid 'unknown' in internal code. Use domain types; reserve 'unknown' for external boundaries (I/O, JSON, external APIs)  @typescript-eslint/no-restricted-types
  52:21  error    Do not use 'as' assertions. Prefer precise types or type guards                                                                                          no-restricted-syntax
  52:21  error    Unsafe assertion from `any` detected: consider using type guards or a safer assertion                                                                    @typescript-eslint/no-unsafe-type-assertion
  52:44  warning  Don't use `unknown` as a type. Avoid 'unknown' in internal code. Use domain types; reserve 'unknown' for external boundaries (I/O, JSON, external APIs)  @typescript-eslint/no-restricted-types

Γ£û 93 problems (87 errors, 6 warnings)

npm error Lifecycle script `lint` failed with error:
npm error code 1
npm error path C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend
npm error workspace frontend@1.0.0
npm error location C:\Users\cyril.beurier\code\Azure-Architect-Assistant-archchatbot\frontend
npm error command failed
npm error command C:\WINDOWS\system32\cmd.exe /d /s /c eslint --report-unused-disable-directives 
